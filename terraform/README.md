# Terraform インフラ管理

`docs/project-spec.md` の低コスト学習構成を管理します。AWSへの適用は別途承認後に行います。

## 構成

- 既存Route 53ゾーンに公開用A/AAAA、オリジン用A、ACM検証レコードを作成。
- CloudFront + us-east-1のACM証明書。動的ページはキャッシュ無効、Cookie・クエリ・Hostを含むヘッダーを転送。`/static/*`・`/media/*`は非公開S3へOACでアクセス。
- EC2 1台（t4g.micro、Amazon Linux 2023 ARM64）。Docker / ARM64 Composeを導入。Elastic IPなし、SSHなし。Session Managerを使用。
- EC2への受信はCloudFrontのIPv4プレフィックスリストからHTTP 80のみ。閲覧者→CloudFrontはHTTPS、CloudFront→EC2はHTTP。
- PostgreSQL 15（db.t4g.micro、Single-AZ）、非公開DBサブネット2つ。既存の未使用パブリックサブネットは移行時の不要な削除を避けて維持。
- RDS自動バックアップ7日、削除保護とTerraformのprevent_destroy。既存S3バージョニングを維持。
- Parameter Store SecureStringにアプリの秘密情報とDB接続設定を保存。EC2ロールに対象パラメータ取得・S3配信対象プレフィックスへの読み書き・Session Manager接続を許可。
- CloudWatchでEC2ステータス、Lambdaエラー、RDS空き容量を監視。アラームはコンソール確認用で、メール送信アクションは未設定。Lambdaログは7日保持。
- AWS Budgetsはアカウント全体を対象に、指定為替で3,000円相当のUSD予算、1,500/2,000/2,500円相当のメール通知。

## 設定・検証

Terraform >= 1.5とAWS認証情報が必要です。既存のパブリックホストゾーンと利用するドメインを準備してください。

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# tfvarsにドメイン、ゾーンID、予算メール・換算レート、当年の祝日一覧を設定
# TF_VAR_db_password / TF_VAR_django_secret_keyを安全な方法で環境変数に設定
terraform init
terraform fmt -check
terraform validate
python3 -m unittest discover -s tests -v
terraform plan -out=tfplan
```

`tfvars`・state・planには秘密情報が含まれ得ます。Git管理対象外です。リモートstateを使う場合は暗号化・アクセス制限を設定してください。

planでEC2置換、Elastic IP削除、DNS変更、IAM追加と想定料金を確認し、承認後にだけ`terraform apply tfplan`を実行します。DB・ストレージを削除・置換する場合は先に復旧可能なバックアップを確認してください。destroyは実行しません。

## 起動・停止

Schedulerが日本時間で5分ごとにLambdaを呼びます。平日10:00〜22:00かつ`holiday_dates`以外を起動対象とします。10:00にRDS起動を開始し、利用可能になった後の実行でEC2を起動、さらにrunning確認後にオリジンAレコードを更新します。起動処理とDNS伝播のため10:00ちょうどの利用開始は保証しません。

停止時間はEC2停止→stopped確認→RDS停止の順です。処理中のリソースは次回に再確認するためLambda内で長時間待ちません。長期停止後にRDSが自動起動しても停止時間帯のチェックで再停止します。失敗はログとLambda Errorsアラームで確認し、5分後に再試行します。

祝日一覧は利用者が当年分を入力し、毎年`holiday_calendar_year`とともに更新します。対象年が古くなると安全側で停止処理を行い、起動せずエラーを記録します。空リストでは祝日を除外できません。

即時再試行も現在の時刻に従います。

```bash
aws lambda invoke --function-name yakugaku-quiz-schedule --payload '{}' /tmp/yakugaku-schedule-result.json
```

時間外の手動利用時はSchedulerを一時無効化し、RDSがavailableになってからEC2を起動、取得したPublic IPv4でオリジンAを更新してください。終了後はEC2→RDSの順に停止し、Schedulerを有効に戻します。初回apply直後のEC2/RDSは起動しており、時間外なら最初の定期実行から順に停止します。

## アプリの配置

TerraformはAWS基盤とDocker導入までです。アプリの配置、Nginx/Gunicornの本番設定、Composeの自動再起動、Parameter Storeから環境変数への読み込み、S3へのcollectstatic/media保存は別途設定が必要です。

- Session Managerで接続し、ARM64対応イメージを使用する。
- `ALLOWED_HOSTS`に公開ドメイン、`CSRF_TRUSTED_ORIGINS`にそのHTTPS URLを設定する。
- CloudFront→NginxがHTTPのため、Nginx側で転送元を踏まえてHTTPS情報を正しく設定し、Djangoの`SECURE_PROXY_SSL_HEADER`と整合させる。`$scheme`をそのまま渡すとリダイレクトループの原因になる。
- S3のオブジェクトキーは`static/`・`media/`配下とする。個人情報や認証必須のファイルをこの公開配信パスに置かない。

CloudFrontプレフィックスリストは他アカウントの配信も含むため、特定distributionの限定にはアプリ側のオリジン検証も必要です。プレフィックスリストの重みは55のため、80/443両方のルール追加は標準SGクォータを超える可能性があります。

## 料金・移行

月額3,000円は目標で、保証ではありません。停止中もEBS・RDSストレージ、バックアップ、S3、Route 53等の料金が残り、稼働中はPublic IPv4も課金対象です。転送量・為替・既存アカウント利用料で変動するため、apply前にAWS Pricing Calculatorで見積もってください。予算通知はリソースを停止しません。

既存t3.microからの移行ではARM AMIへのEC2置換によりルートEBSも置換されます。コード・メディア・設定の退避とARM64対応を確認してください。Elastic IP解放で旧IPは使えなくなります。RDS/S3/VPCのリソース名を維持し、DBの暗号化設定変更など置換を伴う変更は含めていません。既存DNSレコードがある場合は上書きせず、対象を確認してimportしてください。

参考: [CloudFrontプレフィックスリスト](https://docs.aws.amazon.com/ja_jp/vpc/latest/userguide/working-with-aws-managed-prefix-lists.html)、[RDS起動](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StartInstance.html)

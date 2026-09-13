from collections import Counter

from django.core.exceptions import ValidationError
from import_export import resources

from .models import Question


QUESTION_COLUMNS = (
    'question_code', 'text', 'choice1', 'choice2', 'choice3', 'choice4',
    'choice5', 'choice6', 'correct', 'explanation', 'category', 'question_type',
)

OPTIONAL_COLUMNS = ('choice5', 'choice6')
REQUIRED_COLUMNS = tuple(name for name in QUESTION_COLUMNS if name not in OPTIONAL_COLUMNS)


class QuestionResource(resources.ModelResource):
    class Meta:
        model = Question
        fields = QUESTION_COLUMNS
        import_order = QUESTION_COLUMNS
        export_order = QUESTION_COLUMNS
        import_id_fields = ('question_code',)
        clean_model_instances = True
        use_transactions = True

    def import_data(self, dataset, dry_run=False, raise_errors=False,
                    use_transactions=None, collect_failed_rows=False,
                    rollback_on_validation_errors=True, **kwargs):
        # Preview and confirmed imports must both remain all-or-nothing.
        return super().import_data(
            dataset, dry_run=dry_run, raise_errors=raise_errors,
            use_transactions=True, collect_failed_rows=collect_failed_rows,
            rollback_on_validation_errors=True, **kwargs,
        )

    def before_import(self, dataset, **kwargs):
        self.seen_codes = set()
        headers = dataset.headers or []
        missing = [name for name in REQUIRED_COLUMNS if name not in headers]
        duplicate = [name for name, count in Counter(headers).items() if count > 1]
        if missing or duplicate:
            errors = []
            if missing:
                errors.append('必須カラムがありません: ' + ', '.join(missing))
            if duplicate:
                errors.append('ヘッダーが重複しています: ' + ', '.join(duplicate))
            raise ValidationError(errors)

    def before_import_row(self, row, **kwargs):
        errors = {}
        for name in QUESTION_COLUMNS:
            if name in OPTIONAL_COLUMNS and name not in row:
                continue
            value = row.get(name)
            row[name] = '' if value is None else str(value).strip()
            if name in REQUIRED_COLUMNS and not row[name]:
                errors[name] = '必須項目です。'

        code = row['question_code']
        if code:
            if code in self.seen_codes:
                errors['question_code'] = 'CSV内で question_code が重複しています。'
            self.seen_codes.add(code)

        if errors:
            raise ValidationError(errors)

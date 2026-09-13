from django.contrib import admin
from django.template.response import TemplateResponse
from import_export.admin import ImportMixin
from import_export.formats.base_formats import CSV

from .models import Question, Answer
from .resources import QuestionResource


@admin.register(Question)
class QuestionAdmin(ImportMixin, admin.ModelAdmin):
    resource_classes = [QuestionResource]
    formats = [CSV]
    from_encoding = 'utf-8-sig'
    skip_import_confirm = False

    def has_import_permission(self, request):
        return self.has_add_permission(request) and self.has_change_permission(request)

    def process_result(self, result, request):
        if result.has_errors() or result.has_validation_errors():
            context = self.admin_site.each_context(request)
            context.update(
                title='CSVインポートエラー', opts=self.model._meta, result=result,
                import_error_display=('message',),
            )
            return TemplateResponse(request, 'admin/quiz/question/import_error.html', context)
        return super().process_result(result, request)


admin.site.register(Answer)

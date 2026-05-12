from django.db import models


class Case(models.Model):
    case_id = models.CharField(max_length=32, unique=True, db_index=True)
    axis_id = models.CharField(max_length=64, db_index=True)
    file_name = models.CharField(max_length=512, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.case_id} [{self.axis_id}]"


class Result(models.Model):
    case = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="result")
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Result<{self.case.case_id}>"

"""Response shape mirrors `AnalysisResult` in src/lib/mockApi.ts.

We don't strictly serialize on the way out (the view returns a plain dict)
but these serializers document and validate the contract.
"""
from rest_framework import serializers


class ConfidenceItem(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.FloatField(min_value=0.0, max_value=1.0)


class RegionItem(serializers.Serializer):
    region = serializers.CharField()
    side = serializers.ChoiceField(choices=["L", "R", "B"])
    contribution = serializers.FloatField()


class SignalPoint(serializers.Serializer):
    t = serializers.IntegerField()
    v = serializers.FloatField()


class TimelineEvent(serializers.Serializer):
    t = serializers.IntegerField()
    label = serializers.CharField()
    severity = serializers.ChoiceField(choices=["low", "moderate", "high"])


class MetricItem(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()


class AnalysisResultSerializer(serializers.Serializer):
    axisId = serializers.CharField()
    caseId = serializers.CharField()
    predictedClass = serializers.CharField()
    topConfidence = serializers.FloatField()
    summary = serializers.CharField()
    disclaimer = serializers.CharField()
    confidence = ConfidenceItem(many=True)
    regions = RegionItem(many=True)
    signal = SignalPoint(many=True, required=False)
    timeline = TimelineEvent(many=True, required=False)
    network = serializers.DictField(required=False)
    metrics = MetricItem(many=True, required=False)


class AnalyzeRequestSerializer(serializers.Serializer):
    file = serializers.FileField(required=False)
    metadata = serializers.JSONField(required=False)

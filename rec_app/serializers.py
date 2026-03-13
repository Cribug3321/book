from rest_framework import serializers
from .models import Book, UserProfile, Rating


class BookSerializer(serializers.ModelSerializer):
    # 新增只读字段：用于存放数据库聚合计算出的平均分
    avg_rating = serializers.FloatField(read_only=True, default=0.0)

    # 新增只读字段：用于存放当前登录用户对这本书的历史打分记录
    user_rating = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Book
        fields = [
            'isbn',
            'title',
            'author',
            'year',
            'publisher',
            'avg_rating',  # 暴露给前端的平均分
            'user_rating'  # 暴露给前端的用户自身评分
        ]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        # 既然我们前面给用户表增加了用户名，这里最好也加上 username 字段
        fields = ['user_id', 'age', 'username']


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['user', 'book', 'rating']

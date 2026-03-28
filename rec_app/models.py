from django.db import models


class Book(models.Model):
    isbn = models.CharField(max_length=20, primary_key=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=255, null=True, blank=True)

    # 性能优化字段：避免实时计算，改为读取预存数据
    avg_rating = models.FloatField(default=0.0)
    num_ratings = models.IntegerField(default=0)

    # === 新增字段：记录添加时间 ===
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.title


class UserProfile(models.Model):
    user_id = models.IntegerField(primary_key=True)
    age = models.IntegerField(null=True, blank=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)

    # 必须有这个字段
    is_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username if self.username else f"User: {self.user_id}"


class Rating(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.IntegerField()

    def __str__(self):
        return f"{self.user_id} - {self.book_id}: {self.rating}"
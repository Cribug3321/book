import pandas as pd
from django.core.management.base import BaseCommand
from rec_app.models import UserProfile, Book, Rating


class Command(BaseCommand):
    help = 'Load CSV data into MySQL database'

    def handle(self, *args, **kwargs):
        self.stdout.write("开始加载并清洗数据，这可能需要几分钟的时间...")

        # ==========================================
        # 1. 导入 Users 数据
        # ==========================================
        self.stdout.write("-> 正在处理 users.csv ...")
        # Users 往往也是 latin-1 编码，这里一并改掉以防万一
        df_users = pd.read_csv('users.csv', sep=';', encoding='latin-1', on_bad_lines='skip', low_memory=False)
        df_users.rename(columns={'User-ID': 'user_id', 'Age': 'age'}, inplace=True)

        df_users['user_id'] = pd.to_numeric(df_users['user_id'], errors='coerce')
        df_users.dropna(subset=['user_id'], inplace=True)
        df_users['user_id'] = df_users['user_id'].astype(int)

        df_users['age'] = pd.to_numeric(df_users['age'], errors='coerce')
        df_users['age'] = df_users['age'].fillna(-1).astype(int)

        user_objs = [
            UserProfile(
                user_id=row['user_id'],
                age=None if row['age'] == -1 else row['age']
            )
            for _, row in df_users.iterrows()
        ]
        UserProfile.objects.bulk_create(user_objs, batch_size=5000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"成功导入 Users 数据！"))

        # ==========================================
        # 2. 导入 Books 数据
        # ==========================================
        self.stdout.write("-> 正在处理 books.csv ...")
        # 【修改点】：将 encoding='utf-8' 改为了 encoding='latin-1'
        df_books = pd.read_csv('books.csv', sep=';', encoding='latin-1', on_bad_lines='skip', low_memory=False)
        df_books.rename(
            columns={'ISBN': 'isbn', 'Title': 'title', 'Author': 'author', 'Year': 'year', 'Publisher': 'publisher'},
            inplace=True)

        df_books['isbn'] = df_books['isbn'].astype(str)
        df_books.dropna(subset=['isbn'], inplace=True)
        df_books.fillna('', inplace=True)

        book_objs = [
            Book(
                isbn=row['isbn'][:20],
                title=str(row['title'])[:250],
                author=str(row['author'])[:250],
                year=str(row['year'])[:10],
                publisher=str(row['publisher'])[:250]
            )
            for _, row in df_books.iterrows()
        ]
        Book.objects.bulk_create(book_objs, batch_size=5000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"成功导入 Books 数据！"))

        # ==========================================
        # 3. 导入 Ratings 数据
        # ==========================================
        self.stdout.write("-> 正在处理 ratings.csv ...")
        # 【修改点】：将 encoding='utf-8' 改为了 encoding='latin-1'
        df_ratings = pd.read_csv('ratings.csv', sep=';', encoding='latin-1', on_bad_lines='skip', low_memory=False)
        df_ratings.rename(columns={'User-ID': 'user_id', 'ISBN': 'isbn', 'Rating': 'rating'}, inplace=True)

        df_ratings['user_id'] = pd.to_numeric(df_ratings['user_id'], errors='coerce')
        df_ratings['rating'] = pd.to_numeric(df_ratings['rating'], errors='coerce')
        df_ratings.dropna(subset=['user_id', 'rating', 'isbn'], inplace=True)

        df_ratings['user_id'] = df_ratings['user_id'].astype(int)
        df_ratings['isbn'] = df_ratings['isbn'].astype(str)
        df_ratings['rating'] = df_ratings['rating'].astype(int)

        valid_users = set(UserProfile.objects.values_list('user_id', flat=True))
        valid_books = set(Book.objects.values_list('isbn', flat=True))

        df_ratings = df_ratings[df_ratings['user_id'].isin(valid_users)]
        df_ratings = df_ratings[df_ratings['isbn'].isin(valid_books)]

        rating_objs = [
            Rating(
                user_id=row['user_id'],
                book_id=row['isbn'],
                rating=row['rating']
            )
            for _, row in df_ratings.iterrows()
        ]
        Rating.objects.bulk_create(rating_objs, batch_size=5000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"成功导入 Ratings 数据！数据初始化全部完成！"))
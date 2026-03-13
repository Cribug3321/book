from django.urls import path
from rec_app.views import (
    BookListView,
    RecommendView,
    register_user,
    login_user,
    rate_book,
    RatedBooksView,
    AdminBookView,   # 导入新增的图书管理视图
    AdminUserView    # 导入新增的用户管理视图
)

urlpatterns = [
    # 原有基础路由
    path('books/', BookListView.as_view(), name='book-list'),
    path('recommend/', RecommendView.as_view(), name='book-recommend'),
    path('register/', register_user, name='register'),
    path('login/', login_user, name='login'),
    path('rate/', rate_book, name='rate'),
    path('rated/', RatedBooksView.as_view(), name='rated-books'),

    # ===== 新增：管理员功能路由 =====
    # 管理员书籍管理 (POST /admin/books/ 加书，DELETE /admin/books/?isbn=xxx 删书)
    path('admin/books/', AdminBookView.as_view(), name='admin-books'),
    # 管理员用户管理 (DELETE /admin/users/?user_id=xxx 删用户)
    path('admin/users/', AdminUserView.as_view(), name='admin-users'),
]
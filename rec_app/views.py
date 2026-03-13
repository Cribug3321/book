from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view
from django.db.models import Avg, Count, Case, When, Q, OuterRef, Subquery, Max
from .models import Book, UserProfile, Rating
from .serializers import BookSerializer
from .recommender import recommender


# ==========================================
# 1. 分页器设置
# ==========================================
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ==========================================
# 2. 图书大厅接口 (支持分类搜索与权限透出)
# ==========================================
class BookListView(generics.ListAPIView):
    serializer_class = BookSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Book.objects.all()

        # 获取前端传来的参数
        search_keyword = self.request.query_params.get('search', '').strip()
        search_type = self.request.query_params.get('search_type', 'all')  # 新增：搜索字段选项
        scope = self.request.query_params.get('scope', 'user')  # 新增：场景（admin或user）
        user_id = self.request.query_params.get('user_id')

        # 1. 搜索过滤逻辑
        if search_keyword:
            if search_type == 'isbn':
                queryset = queryset.filter(isbn__icontains=search_keyword)
            elif search_type == 'title':
                queryset = queryset.filter(title__icontains=search_keyword)
            elif search_type == 'author':
                queryset = queryset.filter(author__icontains=search_keyword)
            else:
                # 默认 'all'：三字段全模糊匹配
                queryset = queryset.filter(
                    Q(title__icontains=search_keyword) |
                    Q(author__icontains=search_keyword) |
                    Q(isbn__icontains=search_keyword)
                )

        # 2. 权限与排序隔离逻辑
        if scope == 'admin':
            # 【管理员视角】：不过滤评价数，展示全库所有书籍。
            # 默认按 isbn 倒序（通常是最新添加的书排在前面），方便管理
            queryset = queryset.order_by('-isbn')
        else:
            # 【普通用户视角】：如果没有搜索关键字，默认只推荐评价数大于5的好书
            if not search_keyword:
                queryset = queryset.filter(num_ratings__gt=5)
            # 用户视角永远按热度和口碑排序
            queryset = queryset.order_by('-num_ratings', '-avg_rating')

        # 3. 挂载当前登录用户的打分状态
        if user_id:
            user_rating_sq = Rating.objects.filter(
                book=OuterRef('pk'),
                user_id=user_id
            ).values('rating')[:1]
            queryset = queryset.annotate(user_rating=Subquery(user_rating_sq))

        return queryset


# ==========================================
# 3. 专属个性化推荐接口 (优化性能版)
# ==========================================
class RecommendView(APIView):
    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({"error": "请提供 user_id 参数"}, status=400)

        def annotate_user_rating(qs):
            sq = Rating.objects.filter(book=OuterRef('pk'), user_id=user_id).values('rating')[:1]
            return qs.annotate(user_rating=Subquery(sq))

        try:
            top_isbns = recommender.get_top_n_recommendations(user_id, n=10)

            if not top_isbns:
                recent_ratings = Rating.objects.filter(user_id=user_id, rating__gte=6).select_related('book')
                if recent_ratings.exists():
                    liked_authors = [r.book.author for r in recent_ratings if r.book.author]
                    rated_isbns = [r.book.isbn for r in recent_ratings]

                    warm_books = Book.objects.filter(
                        author__in=liked_authors
                    ).exclude(isbn__in=rated_isbns).order_by('-avg_rating')[:10]

                    if warm_books.exists():
                        warm_books = annotate_user_rating(warm_books)
                        serializer = BookSerializer(warm_books, many=True)
                        return Response({
                            "status": "warm_start",
                            "message": "系统正在学习您的喜好！在此期间，基于您刚刚的高分评价，为您推荐同作者的其他佳作：",
                            "data": serializer.data
                        })

                fallback_books = Book.objects.filter(num_ratings__gt=5).order_by('-avg_rating')[:10]
                fallback_books = annotate_user_rating(fallback_books)
                serializer = BookSerializer(fallback_books, many=True)
                return Response({
                    "status": "cold_start",
                    "message": "系统暂时还没有摸透你的喜好。以下为您推荐全站评分最高的书籍：",
                    "data": serializer.data
                })

            preserved_order = Case(*[When(isbn=isbn, then=pos) for pos, isbn in enumerate(top_isbns)])
            recommended_books = Book.objects.filter(isbn__in=top_isbns).order_by(preserved_order)

            recommended_books = annotate_user_rating(recommended_books)
            serializer = BookSerializer(recommended_books, many=True)
            return Response({
                "status": "success",
                "message": "系统为您生成了 10 本专属推荐！",
                "data": serializer.data
            })

        except Exception as e:
            print(f"Recommend Error: {str(e)}")
            return Response({"error": str(e)}, status=500)


# ==========================================
# 4. 注册/登录/打分/已读 (核心业务逻辑)
# ==========================================
@api_view(['POST'])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'error': '用户名和密码不能为空'}, status=400)
    if UserProfile.objects.filter(username=username).exists():
        return Response({'error': '用户名已存在'}, status=400)

    max_id = UserProfile.objects.aggregate(Max('user_id'))['user_id__max'] or 0
    user = UserProfile.objects.create(user_id=max_id + 1, username=username, password=password)
    return Response({'message': '注册成功', 'user_id': user.user_id, 'username': user.username})


@api_view(['POST'])
def login_user(request):
    account, password = request.data.get('username'), request.data.get('password')
    if not account or not password:
        return Response({'error': '不能为空'}, status=400)

    user = UserProfile.objects.filter(user_id=int(account) if account.isdigit() else -1, password=password).first()
    if not user:
        user = UserProfile.objects.filter(username=account, password=password).first()

    if user:
        return Response({
            'message': '登录成功',
            'user_id': user.user_id,
            'username': user.username or f"老读者_{user.user_id}",
            'is_admin': user.is_admin  # 返回管理员状态
        })
    return Response({'error': '账号或密码错误'}, status=400)


@api_view(['POST'])
def rate_book(request):
    user_id = request.data.get('user_id')
    isbn = request.data.get('isbn')
    rating_val = request.data.get('rating')

    if not user_id or not isbn or rating_val is None:
        return Response({'error': '缺少必要参数'}, status=400)

    try:
        user = UserProfile.objects.get(user_id=user_id)
        book = Book.objects.get(isbn=isbn)

        # 核心逻辑：允许重复打分，但数据库只保留最新一次
        Rating.objects.filter(user=user, book=book).delete()
        Rating.objects.create(user=user, book=book, rating=int(rating_val))

        stats = Rating.objects.filter(book=book).aggregate(avg=Avg('rating'), count=Count('rating'))
        book.avg_rating = stats['avg'] or 0.0
        book.num_ratings = stats['count'] or 0
        book.save()

        return Response({'message': '评分已更新为最新！'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


class RatedBooksView(APIView):
    def get(self, request):
        user_id = request.query_params.get('user_id')
        ratings = Rating.objects.filter(user_id=user_id).select_related('book').order_by('-id')
        data = [{'isbn': r.book.isbn, 'title': r.book.title, 'author': r.book.author, 'year': r.book.year,
                 'publisher': r.book.publisher, 'user_rating': r.rating} for r in ratings]
        return Response({"status": "success", "data": data})


# ==========================================
# 5. 管理员专属接口 (带权限校验)
# ==========================================
def check_is_admin(user_id):
    if not user_id: return False
    try:
        user = UserProfile.objects.get(user_id=user_id)
        return user.is_admin
    except UserProfile.DoesNotExist:
        return False


class AdminBookView(APIView):
    def post(self, request):
        operator_id = request.data.get('operator_id')
        if not check_is_admin(operator_id):
            return Response({"error": "权限拒绝：您不是管理员"}, status=status.HTTP_403_FORBIDDEN)

        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "书籍添加成功", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        operator_id = request.query_params.get('operator_id')
        if not check_is_admin(operator_id):
            return Response({"error": "权限拒绝：您不是管理员"}, status=status.HTTP_403_FORBIDDEN)

        isbn = request.query_params.get('isbn')
        if not isbn:
            return Response({"error": "请提供要删除书籍的 isbn"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            book = Book.objects.get(isbn=isbn)
            book.delete()
            return Response({"message": f"书籍 {isbn} 已成功删除"}, status=status.HTTP_200_OK)
        except Book.DoesNotExist:
            return Response({"error": "书籍不存在"}, status=status.HTTP_404_NOT_FOUND)


class AdminUserView(APIView):
    def get(self, request):
        """获取所有新注册的用户列表（排除原始训练集的老用户）"""
        operator_id = request.query_params.get('operator_id')
        if not check_is_admin(operator_id):
            return Response({"error": "权限拒绝：您不是管理员"}, status=status.HTTP_403_FORBIDDEN)

        # 核心过滤逻辑：
        # 1. username__isnull=False 且不为空 -> 说明是系统里新注册的用户，过滤掉了原始 csv 导入的老用户
        # 2. exclude(user_id=operator_id) -> 把当前管理员自己隐藏掉，防止误删自己
        users = UserProfile.objects.filter(
            username__isnull=False
        ).exclude(
            username=''
        ).exclude(
            user_id=operator_id
        ).order_by('-user_id')  # 按注册时间倒序排

        user_data = []
        for u in users:
            user_data.append({
                "user_id": u.user_id,
                "username": u.username,
                "is_admin": u.is_admin
            })

        return Response({"status": "success", "data": user_data}, status=status.HTTP_200_OK)

    def delete(self, request):
        """删除用户及其所有关联数据，并同步更新图书的冗余评分字段"""
        operator_id = request.query_params.get('operator_id')
        if not check_is_admin(operator_id):
            return Response({"error": "权限拒绝：您不是管理员"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({"error": "请提供要删除用户的 user_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserProfile.objects.get(user_id=user_id)

            # ================= 核心修复：处理数据一致性 =================
            # 1. 在删除用户之前，先查出这个用户评价过的所有图书，存进内存列表
            # （如果不提前存列表，用户一删，就查不到他评价过哪些书了）
            affected_books = list(Book.objects.filter(rating__user=user))

            # 2. 执行删除操作（数据库会自动清理底层的 Rating 记录）
            user.delete()

            # 3. 重新计算这些受影响图书的最新分数
            books_to_update = []
            for book in affected_books:
                stats = Rating.objects.filter(book=book).aggregate(
                    avg=Avg('rating'),
                    count=Count('rating')
                )
                book.avg_rating = stats['avg'] or 0.0
                book.num_ratings = stats['count'] or 0
                books_to_update.append(book)

            # 4. 批量执行更新，避免 for 循环里疯狂请求数据库导致卡顿
            if books_to_update:
                Book.objects.bulk_update(books_to_update, ['avg_rating', 'num_ratings'])
            # ==========================================================

            return Response({
                "message": f"用户 {user.username} (ID:{user_id}) 已销毁。已同步刷新了受影响的 {len(books_to_update)} 本图书评分！"
            }, status=status.HTTP_200_OK)

        except UserProfile.DoesNotExist:
            return Response({"error": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # 捕获其他意外错误
            return Response({"error": f"删除过程中发生错误: {str(e)}"}, status=500)
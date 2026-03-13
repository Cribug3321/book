import os
import sys
import json
import torch
from django.conf import settings
from .models import Book, Rating

# 将 ml_model 目录加入系统路径，以便导入模型结构
ML_DIR = os.path.join(settings.BASE_DIR, 'ml_model')
sys.path.append(ML_DIR)
from model import NCF


class NCFRecommender:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 加载特征映射字典
        with open(os.path.join(ML_DIR, 'user2idx.json'), 'r', encoding='utf-8') as f:
            self.user2idx = json.load(f)
        with open(os.path.join(ML_DIR, 'isbn2idx.json'), 'r', encoding='utf-8') as f:
            self.isbn2idx = json.load(f)

        # 翻转字典：用于将预测出的 index 转回真实的 ISBN
        self.idx2isbn = {idx: isbn for isbn, idx in self.isbn2idx.items()}

        num_users = len(self.user2idx)
        num_books = len(self.isbn2idx)

        # 初始化并加载模型权重
        self.model = NCF(num_users, num_books, embed_size=32).to(self.device)
        model_path = os.path.join(ML_DIR, 'ncf_weights.pth')
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()  # 开启评估模式
        print("NCF 模型加载成功！")

    def get_top_n_recommendations(self, user_id, n=10):
        # JSON 的 key 默认是字符串，转换一下
        str_user_id = str(user_id)
        if str_user_id not in self.user2idx:
            # 冷启动问题：如果是新用户，模型没见过，直接返回空或热门推荐（此处简化为返回空列表）
            return []

        user_idx = self.user2idx[str_user_id]

        # 1. 找出该用户已经评过分的书 (真实 ISBN)
        rated_books = set(Rating.objects.filter(user_id=user_id).values_list('book_id', flat=True))

        # 2. 找出未读过的图书的 index 列表
        unread_book_indices = []
        for isbn, idx in self.isbn2idx.items():
            if isbn not in rated_books:
                unread_book_indices.append(idx)

        if not unread_book_indices:
            return []

        # 3. 构造 PyTorch Tensor 喂给模型
        user_tensor = torch.full((len(unread_book_indices),), user_idx, dtype=torch.long).to(self.device)
        book_tensor = torch.tensor(unread_book_indices, dtype=torch.long).to(self.device)

        # 4. 批量预测评分 (使用 torch.no_grad() 节省内存并加速)
        with torch.no_grad():
            predictions = self.model(user_tensor, book_tensor)

        # 5. 取出分数最高的 Top-N 的索引
        # 注意：如果未读的书少于 N 本，取实际数量
        top_k = min(n, len(unread_book_indices))
        top_scores, top_indices_tensor = torch.topk(predictions, top_k)

        # 6. 将模型输出的局部索引，映射回原始的 book_idx
        recommended_isbns = []
        for local_idx in top_indices_tensor.tolist():
            book_idx = unread_book_indices[local_idx]
            recommended_isbns.append(self.idx2isbn[book_idx])

        return recommended_isbns


# 实例化一个全局单例，防止每次 API 请求都重新加载模型（非常耗时）
recommender = NCFRecommender()
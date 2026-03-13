import os
import sys
import json
import torch
import pandas as pd
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# ==========================================
# 0. 挂载 Django 环境 (核心修改点)
# ==========================================
# 获取当前文件所在目录的上一级目录 (即项目根目录)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
# 设置 Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BookRecSystem.settings')
import django

django.setup()

# 环境挂载完毕后，现在可以安全地导入 Django 的数据库模型了！
from rec_app.models import Rating
from model import NCF


# ==========================================
# 1. 定义 PyTorch 的 Dataset 数据集加载器
# ==========================================
class RatingDataset(Dataset):
    def __init__(self, users, books, ratings):
        self.users = torch.tensor(users, dtype=torch.long)
        self.books = torch.tensor(books, dtype=torch.long)
        self.ratings = torch.tensor(ratings, dtype=torch.float32)

    def __len__(self):
        return len(self.ratings)

    def __getitem__(self, idx):
        return self.users[idx], self.books[idx], self.ratings[idx]


# ==========================================
# 2. 从 MySQL 读取数据与 ID 映射
# ==========================================
def preprocess_data():
    print("正在从 MySQL 数据库提取最新的评分数据...")

    # 直接使用 Django ORM 从数据库中拉取数据，摒弃老旧的 CSV 文件
    qs = Rating.objects.all().values('user_id', 'book_id', 'rating')
    df = pd.DataFrame.from_records(qs)

    # 数据库里的外键字段默认叫 book_id，改名为 isbn
    df.rename(columns={'book_id': 'isbn'}, inplace=True)

    # 清洗：强制转换类型并丢弃空值
    df['user_id'] = pd.to_numeric(df['user_id'], errors='coerce')
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df.dropna(subset=['user_id', 'isbn', 'rating'], inplace=True)
    df['user_id'] = df['user_id'].astype(int)
    df['isbn'] = df['isbn'].astype(str)

    # 【修复截断问题】：之前用了 head(10万)，会导致在表尾的新数据被抛弃。
    # 这里我们改用 tail 取最新的 10 万条交互记录。如果你的显卡够好，也可以注释掉这行跑全量数据！
    df = df.tail(100000)

    print(f"成功提取 {len(df)} 条数据，正在构建特征映射字典...")
    unique_users = df['user_id'].unique()
    unique_books = df['isbn'].unique()

    user2idx = {int(user): idx for idx, user in enumerate(unique_users)}
    isbn2idx = {str(isbn): idx for idx, isbn in enumerate(unique_books)}

    with open('user2idx.json', 'w', encoding='utf-8') as f:
        json.dump(user2idx, f)
    with open('isbn2idx.json', 'w', encoding='utf-8') as f:
        json.dump(isbn2idx, f)

    df['user_idx'] = df['user_id'].map(user2idx)
    df['book_idx'] = df['isbn'].map(isbn2idx)

    return df, len(unique_users), len(unique_books)


# ==========================================
# 3. 核心训练流程
# ==========================================
def train_model():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"当前使用的计算设备: {device}")

    # 调用修改后的预处理函数（不需要传 CSV 路径了）
    df, num_users, num_books = preprocess_data()
    print(f"参与训练的独立用户数: {num_users}, 独立图书数: {num_books}")

    dataset = RatingDataset(df['user_idx'].values, df['book_idx'].values, df['rating'].values)
    dataloader = DataLoader(dataset, batch_size=512, shuffle=True)

    model = NCF(num_users, num_books, embed_size=32).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    epochs = 5
    print("========== 开始训练模型 ==========")
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_idx, (user_idx, book_idx, rating) in enumerate(dataloader):
            user_idx, book_idx, rating = user_idx.to(device), book_idx.to(device), rating.to(device)

            optimizer.zero_grad()
            prediction = model(user_idx, book_idx)
            loss = criterion(prediction, rating)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

            if (batch_idx + 1) % 50 == 0:
                print(
                    f"Epoch [{epoch + 1}/{epochs}] | Batch [{batch_idx + 1}/{len(dataloader)}] | Loss: {loss.item():.4f}")

        avg_loss = total_loss / len(dataloader)
        print(f"==== Epoch {epoch + 1} 完成 | 平均 Loss: {avg_loss:.4f} ====\n")

    torch.save(model.state_dict(), 'ncf_weights.pth')
    print("🎉 模型训练完毕！权重已保存至: ncf_weights.pth")


if __name__ == '__main__':
    train_model()
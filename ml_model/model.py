import torch
import torch.nn as nn


class NCF(nn.Module):
    def __init__(self, num_users, num_books, embed_size=32, hidden_layers=[64, 32, 16]):
        super(NCF, self).__init__()

        # 1. Embedding 层：将稀疏的 User 和 Book 转换为稠密向量
        self.user_embedding = nn.Embedding(num_users, embed_size)
        self.book_embedding = nn.Embedding(num_books, embed_size)

        # 2. MLP 层：多层全连接神经网络
        layers = []
        input_size = embed_size * 2
        for hidden_size in hidden_layers:
            layers.append(nn.Linear(input_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))  # 加入 Dropout 防止过拟合
            input_size = hidden_size

        self.mlp = nn.Sequential(*layers)

        # 3. 输出层：预测具体的评分 (例如 0-10 分)
        self.output_layer = nn.Linear(input_size, 1)

    def forward(self, user_indices, book_indices):
        # 获取 User 和 Book 的 Embedding 向量
        user_vector = self.user_embedding(user_indices)
        book_vector = self.book_embedding(book_indices)

        # 拼接向量
        cat_vector = torch.cat([user_vector, book_vector], dim=-1)

        # 传入 MLP 进行特征交叉学习
        mlp_output = self.mlp(cat_vector)

        # 输出预测评分
        prediction = self.output_layer(mlp_output)
        return prediction.squeeze()
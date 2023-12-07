import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

file_path = "C:\\Users\\ASUS\\wzyhomework\\pachong.csv"
df = pd.read_csv(file_path, encoding='gbk')

# 找到电影类型的全集
all_categories = set(','.join(df['电影类型']).split(','))

# 生成所有电影类型的哑变量
# 处理电影类型
df['电影类型'] = df['电影类型'].apply(lambda x: set(x.split(',')))

# 生成哑变量
for category in all_categories:
    df[category] = df['电影类型'].apply(lambda x: 1 if category in x else 0)

# # 输出结果
# print("电影类型的全集:", all_categories)
# print("\n生成的哑变量数据集:")
# print(df.head(3))

# # 找到国家的全集
# all_categories = set(','.join(df['出品国家']).split(','))
#
# # 生成所有电影类型的哑变量
# # 处理电影类型
# df['出品国家'] = df['出品国家'].apply(lambda x: set(x.split(',')))
all_countries = set(','.join(df['出品国家']).split(','))  # 找到出品国家的全集
df['出品国家'] = df['出品国家'].apply(lambda x: set(x.split(',')))  # 处理出品国家
for country in all_countries:  # 生成哑变量
    df[country] = df['出品国家'].apply(lambda x: 1 if country in x else 0)

# # 生成哑变量
# for category in all_categories:
#     df[category] = df['出品国家'].apply(lambda x: 1 if category in x else 0)

# 输出结果
print("出品国家的全集:", all_countries)
print("\n生成的哑变量数据集:")
print(df.head(3))

movie_data = df

# 特征工程
# 添加电影名称长度
movie_data['电影名称长度'] = movie_data['电影名称'].apply(len)

# 合并特征
x = movie_data.drop(['电影类型', '电影名称', '出品国家', '累计票房'], axis=1)

# 标签为累积票房
y = movie_data['累计票房']

# 划分数据集
X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=123)
#
# print(X_train)
#
# column_titles = X_train.columns
# print(column_titles)

# 本章需导入：
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# %matplotlib inline
plt.rcParams['font.sans-serif'] = ['SimHei']  # 解决中文显示乱码问题
plt.rcParams['axes.unicode_minus'] = False
import warnings

warnings.filterwarnings(action='ignore')

# 确定树深度
err_test = []
err_train = []
K = np.arange(1, 300, 5)
for D in K:
    classifier = RandomForestRegressor(n_estimators=D, random_state=123)  # 设定随机森林分类器的模型参数
    classifier.fit(X_train, y_train)
    err_test.append(1 - classifier.score(X_test, y_test))
    err_train.append(1 - classifier.score(X_train, y_train))
    print(D)
best_D = K[err_test.index(np.min(err_test))]
print(best_D)
fig = plt.figure(figsize=(20, 8))
plt.grid(True, linestyle='-.')
plt.plot(K, err_test, label="测试误差", linestyle='-')
plt.plot(K, err_train, label="训练误差", linestyle='-')
plt.title('随机森林的拟合优度%.9f(最优参数K=%d)' % ((1 - err_test[err_test.index(np.min(err_test))]), best_D),
          fontsize=14)
plt.xlabel("depth", fontsize=14)
plt.ylabel("误差（1-R方）", fontsize=14)
plt.legend(fontsize=12)
plt.legend()
plt.show()

# 选择回归模型
model = RandomForestRegressor(n_estimators=best_D, random_state=123)

# 训练模型
model.fit(X_train, y_train)

feature_importances = model.feature_importances_
print("特征重要性:", feature_importances)
# base_estimators = model.estimators_
# print("基础决策树列表:", base_estimators)
r2_score = model.score(X_test, y_test)
print("模型在测试集上的R²得分:", r2_score)

title = "Clannad"
category = "爱情,校园"
country = "日本"
year = "2007"
month = "9"
day = "15"
length = "120"
rating = "9.9"
rating_number = "1234567"
wishing_number = "1234567"
first_day_box = "11111111"
first_week_box = "22222222"

fieldnames = ["电影名称", "电影类型", "出品国家", "上映年份", "上映月份", "上映日期", "电影时长", "电影评分",
              "打分人数", "想看人数", "首日票房", "首周票房"]
new_movie = pd.DataFrame([[title, category, country, year, month, day, length, rating, rating_number,
                           wishing_number, first_day_box, first_week_box]], columns=fieldnames)
new_movie['电影类型'] = new_movie['电影类型'].apply(lambda x: set(x.split(',')))  # 处理电影类型
for category in all_categories:
    new_movie[category] = new_movie['电影类型'].apply(lambda x: 1 if category in x else 0)
new_movie['出品国家'] = new_movie['出品国家'].apply(lambda x: set(x.split(',')))  # 处理出品国家
for country in all_countries:  # 生成哑变量
    new_movie[country] = new_movie['出品国家'].apply(lambda x: 1 if country in x else 0)
new_movie['电影名称长度'] = new_movie['电影名称'].apply(len)
X = new_movie.drop(['电影类型', '电影名称', '出品国家'], axis=1)

predicted_box = model.predict(X)[0]

print(f"预测累积票房: {predicted_box}")

import os
import sys
import click
import re
import csv

from flask import Flask, render_template
from flask import request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy  # 导入扩展类
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import login_user
from flask_login import login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor

import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei']  # 解决中文显示乱码问题
plt.rcParams['axes.unicode_minus'] = False
import warnings

warnings.filterwarnings(action='ignore')

### 数据库配置
WIN = sys.platform.startswith('win')
if WIN:  # 如果是 Windows 系统，使用三个斜线
    prefix = 'sqlite:///'
else:  # 否则使用四个斜线
    prefix = 'sqlite:////'

app = Flask(__name__)
# 设置签名所需的密钥
app.config['SECRET_KEY'] = 'dev'  # 等同于 app.secret_key = 'dev'
# SQLAlchemy 数据库连接地址：
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控

# 在扩展类实例化前加载配置
db = SQLAlchemy(app)  # 初始化扩展，传入程序实例app
login_manager = LoginManager(app)

login_manager.login_view = 'login'  # 重定向操作 把 login_manager.login_view 的值设为程序的登录视图端点（函数名）


### 初始化 Flask-Login
@login_manager.user_loader
def load_user(user_id):  # 创建用户加载回调函数，接受用户 ID 作为参数
    user = User.query.get(int(user_id))  # 用 ID 作为 User 模型的主键查询对应的用户
    return user  # 返回用户对象


### 生成管理员账户
@app.cli.command()  # 使用 click.option() 装饰器设置的两个选项分别用来接受输入用户名和密码
@click.option('--username', prompt=True, help='The username used to login.')
# hide_input=True:在命令行中输入密码时不会显示输入内容，confirmation_prompt=True:用户需要确认密码
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    """Create user."""
    db.create_all()

    user = User.query.first()
    if user is not None:  # 若数据库中已存在用户，表示管理员用户已经创建过，接下来会更新用户名和密码
        click.echo('Updating user...')  # 在命令行输出消息
        user.username = username
        user.set_password(password)  # 设置密码 调用User类的set_password函数
    else:  # 输入用户名和密码后，即可创建管理员账户
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password)  # 设置密码
        db.session.add(user)

    db.session.commit()  # 提交数据库会话
    click.echo('Done.')


### 创建数据库模型
class User(db.Model, UserMixin):  # 表名将会是 user（自动生成，小写处理）
    # 声明继承 db.Model
    id = db.Column(db.Integer, primary_key=True)  # 主键
    # db.Integer 整型
    name = db.Column(db.String(20))  # 名字
    ### 安全存储密码
    username = db.Column(db.String(20))  # 用户名
    password_hash = db.Column(db.String(128))  # 密码散列值

    def set_password(self, password):  # 用来设置密码的方法，接受密码作为参数
        self.password_hash = generate_password_hash(password)  # 将生成的密码保持到对应字段

    def validate_password(self, password):  # 用于验证密码的方法，接受密码作为参数
        return check_password_hash(self.password_hash, password)  # 返回布尔值


### 模板上下文处理函数
@app.context_processor
def inject_user():  # 函数名可以随意修改
    user = User.query.first()
    return dict(user=user)  # 需要返回字典，等同于return {'user': user}
    # 这个函数返回的变量（以字典键值对的形式）将会统一注入到每一个模板的上下文环境中，因此可以直接在模板中使用。
    # 后面我们创建的任意一个模板，都可以在模板中直接使用 user 变量。


### 400 错误处理函数
@app.errorhandler(400)
def bad_request(e):
    return render_template('400.html'), 400


### 404 错误处理函数
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


### 500 错误处理函数
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


### 编辑电影条目
@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required
# movie_id是电影条目记录在数据库中的主键值，用来在视图函数里查询对应的电影记录。
def edit(movie_id):
    # 返回对应主键的记录，如果没有找到，则返回 404 错误响应
    movie = Movie.query.get_or_404(movie_id)

    # 获取与该电影相关的导演、主演信息
    director_relation = MovieActorRelation.query.filter_by(movie_id=movie.id, relation_type='导演').first()
    director_name = Actor.query.get(director_relation.actor_id).name if director_relation else '无'
    star_relation = MovieActorRelation.query.filter_by(movie_id=movie.id, relation_type='主演').first()
    star_name = Actor.query.get(star_relation.actor_id).name if star_relation else '无'

    if request.method == 'POST':  # 处理编辑表单的提交请求
        title = request.form['title']
        year = request.form['year']
        month = request.form['month']
        day = request.form['day']
        country = request.form['country']
        type = request.form['type']
        box = request.form['box']
        director = request.form['director']
        star = request.form['star']

        if not title or not year or not month or not day or not country or not type or not box \
                or int(year) > 2024 or int(year) < 1900 or int(month) > 12 or int(month) < 0 or int(day) > 31 \
                or int(day) < 0 or len(title) > 20 or len(country) > 10 or len(type) > 10 or float(box) < 0 \
                or not_digits(year) or not_digits(month) or not_digits(day) or not_chinese(country) \
                or not_chinese(type) or not_digits(box):
            flash('输入错误！')
            return redirect(url_for('edit', movie_id=movie_id))  # 重定向回对应的编辑页面

        # 更新
        movie.title = title
        movie.year = int(year)
        movie.month = int(month)
        movie.day = int(day)
        movie.country = country
        movie.type = type
        movie.box = float(box)

        # 更新导演关系
        if director == "无":
            db.session.delete(director_relation)
        elif director != director_name:
            # 检查输入的导演名是否存在
            director_actor = Actor.query.filter_by(name=director).first()
            if not director_actor:
                flash('查无此导演！')
                return redirect(url_for('edit', movie_id=movie_id))

            # 更新导演关系
            if director_relation:
                director_relation.actor_id = director_actor.id
            else:
                director_relation = MovieActorRelation(movie_id=movie.id, actor_id=director_actor.id,
                                                       relation_type='导演')
                db.session.add(director_relation)

        # 更新主演关系
        if star == "无":
            db.session.delete(star_relation)
        elif star != star_name:
            # 检查输入的导演名是否存在
            star_actor = Actor.query.filter_by(name=star).first()
            if not star_actor:
                flash('查无此主演！')
                return redirect(url_for('edit', movie_id=movie_id))

            # 更新主演关系
            if star_relation:
                star_relation.actor_id = star_actor.id
            else:
                star_relation = MovieActorRelation(movie_id=movie.id, actor_id=star_actor.id, relation_type='主演')
                db.session.add(star_relation)

        db.session.commit()  # 提交数据库会话
        flash('电影条目成功更新~')
        return redirect(url_for('index'))  # 重定向回主页

    return render_template('edit.html', movie=movie, director_name=director_name, star_name=star_name)


### 删除电影条目
@app.route('/movie/delete/<int:movie_id>', methods=['POST'])  # 限定只接受 POST 请求
@login_required  # 登录保护
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)  # 获取电影记录
    db.session.delete(movie)  # 删除对应的记录
    db.session.commit()  # 提交数据库会话
    flash('电影条目成功删除~')
    return redirect(url_for('index'))  # 重定向回主页


### 程序主页
### 在主页视图读取数据库记录
# @app.route('/', methods=['GET', 'POST'])  # 同时接受GET和POST请求
# def index():
#     ### 创建电影条目
#     if request.method == 'POST':  # 判断是否是 POST 请求
#         if not current_user.is_authenticated:  # 仅需要禁止未登录用户创建新条目
#             return redirect(url_for('index'))  # 重定向到主页
#
#     movies = Movie.query.all()  # 读取所有电影记录
#     return render_template('index.html', movies=movies)
from flask_paginate import Pagination


@app.route('/', methods=['GET', 'POST'])  # 同时接受GET和POST请求
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    all_movies = Movie.query.all()  # 读取所有电影记录
    movies = Movie.query.paginate(page=page, per_page=per_page, error_out=False)
    pagination = Pagination(page=page, total=movies.total, per_page=per_page, css_framework='bootstrap4')
    return render_template('index.html', movies=movies.items, pagination=pagination, all_movies=all_movies)


### 编辑影人信息
@app.route('/actor/edit_actor/<int:actor_id>', methods=['GET', 'POST'])
@login_required
def edit_actor(actor_id):
    # 返回对应主键的记录，如果没有找到，则返回 404 错误响应
    actor = Actor.query.get_or_404(actor_id)

    if request.method == 'POST':  # 处理编辑表单的提交请求
        name = request.form['name']
        gender = request.form['gender']
        country = request.form['country']

        if not name or not gender or not country or len(name) > 20 or not (gender == '男' or gender == '女') \
                or len(country) > 10 or not_chinese(country):
            flash('输入错误！')
            return redirect(url_for('edit_actor', actor_id=actor_id))  # 重定向回对应的编辑页面

        # 更新
        actor.name = name
        actor.gender = gender
        actor.country = country

        db.session.commit()  # 提交数据库会话
        flash('影人信息成功更新~')
        return redirect(url_for('actor'))  # 重定向回主页

    return render_template('edit_actor.html', actor=actor)


### 影人页
@app.route('/actor', methods=['GET', 'POST'])  # 同时接受GET和POST请求
def actor():
    if request.method == 'POST':  # 判断是否是 POST 请求
        if not current_user.is_authenticated:  # 仅需要禁止未登录用户创建新条目
            return redirect(url_for('index'))  # 重定向到主页

    page = request.args.get('page', 1, type=int)
    per_page = 10
    all_actors = Actor.query.all()  # 读取所有影人记录
    actors = Actor.query.paginate(page=page, per_page=per_page, error_out=False)
    pagination = Pagination(page=page, total=actors.total, per_page=per_page, css_framework='bootstrap4')

    return render_template('actor.html', actors=actors.items, pagination=pagination, all_actors=all_actors)


### 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # request.form 是一个类似字典的对象
        password = request.form['password']

        if not username or not password:  # 检查用户名和密码是否为空
            flash('输入错误！')
            return redirect(url_for('login'))

        user = User.query.first()

        # 验证用户名和密码是否一致
        if username == user.username and user.validate_password(password):
            login_user(user)  # 登入用户
            flash('成功登录~')
            return redirect(url_for('index'))  # 重定向到主页

        flash('用户名或密码输入错误！')  # 如果验证失败，显示错误消息
        return redirect(url_for('login'))  # 重定向回登录页面

    return render_template('login.html')  # # 渲染并返回登录页面的 HTML 模板


### 登出
@app.route('/logout')
@login_required  # 用于视图保护，后面会详细介绍
def logout():
    logout_user()  # 登出用户
    flash('再见~')
    return redirect(url_for('index'))  # 重定向回首页


### 支持设置用户名字
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']  # 从表单中获取输入的新名称

        if not name or len(name) > 20:
            flash('输入错误！')
            return redirect(url_for('settings'))

        user = User.query.first()
        user.name = name
        db.session.commit()  # 提交数据库会话，保存更改
        flash('用户名成功更新~')  # 通过 Flash 提示用户设置已更新
        return redirect(url_for('index'))  # 重定向到主页

    return render_template('settings.html')  # 渲染并返回设置页面的 HTML 模板


### 录入影人
@app.route('/add_actor', methods=['GET', 'POST'])
@login_required
def add_actor():
    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get('name')
        gender = request.form.get('gender')
        country = request.form.get('country')

        # 检查输入是否合规
        if not name or not gender or not country:
            flash('请输入完整信息！')
            return redirect(url_for('add_actor'))
        if len(name) > 20 or len(country) > 10 or not_chinese(country) or not (gender == '男' or gender == '女'):
            flash('输入错误！')
            return redirect(url_for('add_actor'))

        # 检查演员是否已存在
        existing_actor = Actor.query.filter_by(name=name).first()
        if existing_actor:
            flash('已存在该演员！')
            return redirect(url_for('add_actor'))

        # 如果演员不存在，则创建新演员
        new_actor = Actor(name=name, gender=gender, country=country)
        db.session.add(new_actor)
        db.session.commit()
        flash('影人成功录入~')

        return redirect(url_for('add_actor'))

    return render_template('add_actor.html')


### 录入电影
@app.route('/add_movie', methods=['GET', 'POST'])
@login_required
def add_movie():
    if request.method == 'POST':
        # 获取表单数据
        title = request.form['title']
        year = request.form['year']
        month = request.form['month']
        day = request.form['day']
        country = request.form['country']
        type = request.form['type']
        box = request.form['box']
        director = request.form['director']
        star = request.form['star']

        # 检查输入是否合规
        if not title or not year or not month or not day or not country or not type or not box \
                or int(year) > 2024 or int(year) < 1900 or int(month) > 12 or int(month) < 0 or int(day) > 31 \
                or int(day) < 0 or len(title) > 20 or len(country) > 10 or len(type) > 10 or float(box) < 0 \
                or not_digits(year) or not_digits(month) or not_digits(day) or not_chinese(country) \
                or not_chinese(type) or not_digits(box):
            flash('输入错误！')
            return redirect(url_for('add_movie'))  # 重定向回对应的编辑页面

        # 检查电影是否已存在
        existing_movie = Movie.query.filter_by(title=title).first()
        if existing_movie:
            flash('已存在该电影！')
            return redirect(url_for('add_movie'))

        # 检查影人是否已存在
        existing_director = Actor.query.filter_by(name=director).first()
        existing_star = Actor.query.filter_by(name=star).first()
        if not existing_director or not existing_star:
            flash('不存在该影人！请先录入影人信息！')
            return redirect(url_for('add_movie'))

        # 如果电影不存在且影人已存在，则创建新电影和映射关系
        new_movie = Movie(title=title, year=year, month=month, day=day, country=country, type=type, box=box)

        db.session.add(new_movie)  # 为了获取id 必须先提交new_movie
        db.session.commit()

        new_Relation_director = MovieActorRelation(movie_id=new_movie.id, actor_id=existing_director.id,
                                                   relation_type='导演')
        db.session.add(new_Relation_director)
        db.session.commit()

        new_Relation_star = MovieActorRelation(movie_id=new_movie.id, actor_id=existing_star.id, relation_type='主演')
        db.session.add(new_Relation_star)
        db.session.commit()
        flash('电影成功录入~')

        # 可以选择重定向到演员列表页面或其他页面
        return redirect(url_for('index'))

    return render_template('add_movie.html')


### 查询电影
@app.route('/find_movie', methods=['GET', 'POST'])
def find_movie():
    if request.method == 'POST':
        title = request.form.get('title')
        movie = Movie.query.filter_by(title=title).first()

        if movie is None:
            flash('不存在该电影！')
            return redirect(url_for('find_movie'))
        else:
            director_relation = MovieActorRelation.query.filter_by(movie_id=movie.id, relation_type='导演').first()
            director_name = Actor.query.get(director_relation.actor_id).name if director_relation else '无'
            star_relation = MovieActorRelation.query.filter_by(movie_id=movie.id, relation_type='主演').first()
            star_name = Actor.query.get(star_relation.actor_id).name if star_relation else '无'
            return render_template('find_movie.html', movie=movie, director_name=director_name, star_name=star_name)

    return render_template('find_movie.html')


### 查询影人辅助函数
def get_movie_id_by_title(movies, title):
    for movie in movies:
        if movie.title == title:
            return movie.id
    return None


### 查询影人
@app.route('/find_actor', methods=['GET', 'POST'])
def find_actor():
    if request.method == 'POST':
        name = request.form.get('name')
        actor = Actor.query.filter_by(name=name).first()

        if actor is None:
            flash('不存在该影人！')
            return redirect(url_for('find_actor'))
        else:
            director_relations = MovieActorRelation.query.filter_by(actor_id=actor.id, relation_type='导演').all()
            director_movie_names = [Movie.query.get(relation.movie_id).title for relation in director_relations] \
                if director_relations else ['无']
            star_relations = MovieActorRelation.query.filter_by(actor_id=actor.id, relation_type='主演').all()
            star_movie_names = [Movie.query.get(relation.movie_id).title for relation in star_relations] \
                if star_relations else ['无']

            movies = Movie.query.all()

            return render_template('find_actor.html', actor=actor, movies=movies,
                                   director_movie_names=director_movie_names, star_movie_names=star_movie_names,
                                   get_movie_id_by_title=get_movie_id_by_title)

    return render_template('find_actor.html')


### 票房分析
@app.route('/box_analyse', methods=['GET', 'POST'])
def box_analyse():
    if request.method == 'POST':
        title = request.form.get('title')
        movie = MyMovie.query.filter_by(title=title).first()

        if movie is None:
            flash('不存在该电影！')
            return redirect(url_for('box_analyse'))
        else:
            return render_template('box_analyse.html', movie=movie)

    return render_template('box_analyse.html')


### 票房预测
@app.route('/box_predict', methods=['GET', 'POST'])
def box_predict():
    if request.method == 'POST':
        # 获取表单数据
        title = request.form['title']
        category = request.form['category']
        country = request.form['country']
        year = request.form['year']
        month = request.form['month']
        day = request.form['day']
        length = request.form['length']
        rating = request.form['rating']
        rating_number = request.form['rating_number']
        wishing_number = request.form['wishing_number']
        first_day_box = request.form['first_day_box']
        first_week_box = request.form['first_week_box']

        # 检查输入是否合规
        if not title or not category or not country or not year or not month or not day or not length or not rating \
                or not rating_number or not wishing_number or not first_day_box or not first_week_box\
                or int(year) > 2024 or int(year) < 1900 or int(month) > 12 or int(month) < 0 or int(day) > 31 \
                or int(day) < 0 or int(length) > 1000 or float(rating) > 10 or float(rating) < 0 or len(title) > 20 \
                or len(country) > 10 or not_digits(year) or not_digits(month) or not_digits(day) or not_digits(length)\
                or not_digits(rating) or not_digits(rating_number) or not_digits(wishing_number) \
                or not_digits(first_day_box) or not_digits(first_week_box) or int(first_day_box) > int(first_week_box):
            flash('输入错误！')
            return redirect(url_for('box_predict'))  # 重定向回对应的编辑页面

        # 数据处理
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

        return render_template('box_predict.html', predicted_box=int(predicted_box))

    return render_template('box_predict.html')


### 检查输入的字符串是否全都是汉字
def not_chinese(input_str):
    pattern = re.compile("^[\u4e00-\u9fa5]+$")  # 使用正则表达式匹配字符串是否全都是汉字
    result = pattern.match(input_str)
    return result is None  # 如果字符串全都是汉字，则返回 False


### 检查输入的字符串是否全都是数字
def not_digits(input_str):
    result = input_str.isdigit()
    return result is None  # 如果字符串全都是数字，返回 False


class Movie(db.Model):  # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True)  # 主键
    title = db.Column(db.String(20))  # 电影名称
    year = db.Column(db.Integer)  # 电影上映年份
    month = db.Column(db.Integer)  # 电影上映月份
    day = db.Column(db.Integer)  # 电影上映日期
    country = db.Column(db.String(10))  # 电影出品国家
    type = db.Column(db.String(10))  # 电影类型
    box = db.Column(db.Float)  # 电影票房

    # 添加关联关系
    actors = db.relationship('Actor', secondary='movie_actor_relation', back_populates='movies',
                             cascade='all, delete-orphan', single_parent=True, passive_deletes=True)


class Actor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    gender = db.Column(db.String(1))
    country = db.Column(db.String(10))

    # 添加关联关系
    movies = db.relationship('Movie', secondary='movie_actor_relation', back_populates='actors',
                             cascade='all, delete-orphan', single_parent=True, passive_deletes=True)


class MovieActorRelation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id', ondelete='SET NULL', onupdate='SET NULL'))
    actor_id = db.Column(db.Integer, db.ForeignKey('actor.id', ondelete='SET NULL', onupdate='SET NULL'))
    relation_type = db.Column(db.String(20))

    # 添加关联关系
    movie = db.relationship('Movie', backref=db.backref('movie_actor_relations', cascade='all, delete-orphan',
                                                        passive_deletes=True))
    actor = db.relationship('Actor', backref=db.backref('movie_actor_relations', cascade='all, delete-orphan',
                                                        passive_deletes=True))


class MyMovie(db.Model):  # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True)  # 主键
    title = db.Column(db.String(20))  # 电影名称
    type = db.Column(db.String(10))  # 电影类型
    country = db.Column(db.String(10))  # 电影出品国家
    year = db.Column(db.Integer)  # 电影上映年份
    month = db.Column(db.Integer)  # 电影上映月份
    day = db.Column(db.Integer)  # 电影上映日期
    length = db.Column(db.Float)  # 电影时长
    rating = db.Column(db.Float)  # 电影评分
    rating_number = db.Column(db.Integer)  # 电影打分人数
    wishing_number = db.Column(db.Integer)  # 电影想看人数
    box = db.Column(db.Integer)  # 电影票房
    first_day_box = db.Column(db.Integer)  # 电影首日票房
    first_week_box = db.Column(db.Integer)  # 电影首周票房


### 自定义命令 initdb
@app.cli.command()  # 注册为命令
@click.option('--drop', is_flag=True, help='Create after drop.')
# 设置选项
def initdb(drop):
    """Initialize the database."""
    if drop:  # 判断是否输入了选项
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')  # 输出提示信息


### 创建自定义命令 forge
@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()

    # 添加用户信息
    name = 'Charliewzyyy'

    user = User(name=name)
    db.session.add(user)

    # 添加电影信息
    movies = [
        ('1001', '战狼2', '2017/7/27', '中国', '战争', '2017', 56.84),
        ('1002', '哪吒之魔童降世', '2019/7/26', '中国', '动画', '2019', 50.15),
        ('1003', '流浪地球', '2019/2/5', '中国', '科幻', '2019', 46.86),
        ('1004', '复仇者联盟4', '2019/4/24', '美国', '科幻', '2019', 42.5),
        ('1005', '红海行动', '2018/2/16', '中国', '战争', '2018', 36.5),
        ('1006', '唐人街探案2', '2018/2/16', '中国', '喜剧', '2018', 33.97),
        ('1007', '我不是药神', '2018/7/5', '中国', '喜剧', '2018', 31),
        ('1008', '中国机长', '2019/9/30', '中国', '剧情', '2019', 29.12),
        ('1009', '速度与激情8', '2017/4/14', '美国', '动作', '2017', 26.7),
        ('1010', '西虹市首富', '2018/7/27', '中国', '喜剧', '2018', 25.47),
        ('1011', '复仇者联盟3', '2018/5/11', '美国', '科幻', '2018', 23.9),
        ('1012', '捉妖记2', '2018/2/16', '中国', '喜剧', '2018', 22.37),
        ('1013', '八佰', '2020/08/21', '中国', '战争', '2020', 30.1),
        ('1014', '姜子牙', '2020/10/01', '中国', '动画', '2020', 16.02),
        ('1015', '我和我的家乡', '2020/10/01', '中国', '剧情', '2020', 28.29),
        ('1016', '你好，李焕英', '2021/02/12', '中国', '喜剧', '2021', 54.13),
        ('1017', '长津湖', '2021/09/30', '中国', '战争', '2021', 53.48),
        ('1018', '速度与激情9', '2021/05/21', '中国', '动作', '2021', 13.92),
    ]

    for data in movies:
        movie = Movie(
            id=int(data[0]),
            title=data[1],
            year=data[5],
            month=datetime.strptime(data[2], '%Y/%m/%d').month,
            day=datetime.strptime(data[2], '%Y/%m/%d').day,
            country=data[3],
            type=data[4],
            box=data[6]
        )
        db.session.add(movie)

    # 添加演员信息
    actors_data = [
        ('2001', '吴京', '男', '中国'),
        ('2002', '饺子', '男', '中国'),
        ('2003', '屈楚萧', '男', '中国'),
        ('2004', '郭帆', '男', '中国'),
        ('2005', '乔罗素', '男', '美国'),
        ('2006', '小罗伯特·唐尼', '男', '美国'),
        ('2007', '克里斯·埃文斯', '男', '美国'),
        ('2008', '林超贤', '男', '中国'),
        ('2009', '张译', '男', '中国'),
        ('2010', '黄景瑜', '男', '中国'),
        ('2011', '陈思诚', '男', '中国'),
        ('2012', '王宝强', '男', '中国'),
        ('2013', '刘昊然', '男', '中国'),
        ('2014', '文牧野', '男', '中国'),
        ('2015', '徐峥', '男', '中国'),
        ('2016', '刘伟强', '男', '中国'),
        ('2017', '张涵予', '男', '中国'),
        ('2018', 'F·加里·格雷', '男', '美国'),
        ('2019', '范·迪塞尔', '男', '美国'),
        ('2020', '杰森·斯坦森', '男', '美国'),
        ('2021', '闫非', '男', '中国'),
        ('2022', '沈腾', '男', '中国'),
        ('2023', '安东尼·罗素', '男', '美国'),
        ('2024', '克里斯·海姆斯沃斯', '男', '美国'),
        ('2025', '许诚毅', '男', '中国'),
        ('2026', '梁朝伟', '男', '中国'),
        ('2027', '白百何', '女', '中国'),
        ('2028', '井柏然', '男', '中国'),
        ('2029', '管虎', '男', '中国'),
        ('2030', '王千源', '男', '中国'),
        ('2031', '姜武', '男', '中国'),
        ('2032', '宁浩', '男', '中国'),
        ('2033', '葛优', '男', '中国'),
        ('2034', '范伟', '男', '中国'),
        ('2035', '贾玲', '女', '中国'),
        ('2036', '张小斐', '女', '中国'),
        ('2037', '陈凯歌', '男', '中国'),
        ('2038', '徐克', '男', '中国'),
        ('2039', '易烊千玺', '男', '中国'),
        ('2040', '林诣彬', '男', '美国'),
        ('2041', '米歇尔·罗德里格兹', '女', '美国'),
    ]

    for data in actors_data:
        actor = Actor(
            id=int(data[0]),
            name=data[1],
            gender=data[2],
            country=data[3]
        )
        db.session.add(actor)

    # 添加关系信息
    relations_data = [
        ('1', '1001', '2001', '主演'),
        ('2', '1001', '2001', '导演'),
        ('3', '1002', '2002', '导演'),
        ('4', '1003', '2001', '主演'),
        ('5', '1003', '2003', '主演'),
        ('6', '1003', '2004', '导演'),
        ('7', '1004', '2005', '导演'),
        ('8', '1004', '2006', '主演'),
        ('9', '1004', '2007', '主演'),
        ('10', '1005', '2008', '导演'),
        ('11', '1005', '2009', '主演'),
        ('12', '1005', '2010', '主演'),
        ('13', '1006', '2011', '导演'),
        ('14', '1006', '2012', '主演'),
        ('15', '1006', '2013', '主演'),
        ('16', '1007', '2014', '导演'),
        ('17', '1007', '2015', '主演'),
        ('18', '1008', '2016', '导演'),
        ('19', '1008', '2017', '主演'),
        ('20', '1009', '2018', '导演'),
        ('21', '1009', '2019', '主演'),
        ('22', '1009', '2020', '主演'),
        ('23', '1010', '2021', '导演'),
        ('24', '1010', '2022', '主演'),
        ('25', '1011', '2023', '导演'),
        ('26', '1011', '2006', '主演'),
        ('27', '1011', '2024', '主演'),
        ('28', '1012', '2025', '导演'),
        ('29', '1012', '2026', '主演'),
        ('30', '1012', '2027', '主演'),
        ('31', '1012', '2028', '主演'),
        ('32', '1013', '2029', '导演'),
        ('33', '1013', '2030', '主演'),
        ('34', '1013', '2009', '主演'),
        ('35', '1013', '2031', '主演'),
        ('36', '1015', '2032', '导演'),
        ('37', '1015', '2015', '导演'),
        ('38', '1015', '2011', '导演'),
        ('39', '1015', '2015', '主演'),
        ('40', '1015', '2033', '主演'),
        ('41', '1015', '2034', '主演'),
        ('42', '1016', '2035', '导演'),
        ('43', '1016', '2035', '主演'),
        ('44', '1016', '2036', '主演'),
        ('45', '1016', '2022', '主演'),
        ('46', '1017', '2037', '导演'),
        ('47', '1017', '2038', '导演'),
        ('48', '1017', '2008', '导演'),
        ('49', '1017', '2001', '主演'),
        ('50', '1017', '2039', '主演'),
        ('51', '1018', '2040', '导演'),
        ('52', '1018', '2019', '主演'),
        ('53', '1018', '2041', '主演'),
    ]

    for data in relations_data:
        relation = MovieActorRelation(
            id=int(data[0]),
            movie_id=int(data[1]),
            actor_id=int(data[2]),
            relation_type=data[3]
        )
        db.session.add(relation)

    # 添加票房信息
    file_path = "C:\\Users\\ASUS\\wzyhomework\\pachong.csv"

    with open(file_path, "r", encoding='gbk') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            mymovie = MyMovie(
                title=row['电影名称'],
                type=row['电影类型'],
                country=row['出品国家'],
                year=int(row['上映年份']),
                month=int(row['上映月份']),
                day=int(row['上映日期']),
                length=float(row['电影时长']),
                rating=float(row['电影评分']),
                rating_number=int(row['打分人数']),
                wishing_number=int(row['想看人数']),
                box=int(row['累计票房']),
                first_day_box=int(row['首日票房']),
                first_week_box=int(row['首周票房'])
            )
            db.session.add(mymovie)
            # print(mymovie.title)

    db.session.commit()
    click.echo('Done.')

# 预先生成模型
global model, all_categories, all_countries

file_path = "C:\\Users\\ASUS\\wzyhomework\\pachong.csv"
df = pd.read_csv(file_path, encoding='gbk')

all_categories = set(','.join(df['电影类型']).split(','))  # 找到电影类型的全集
df['电影类型'] = df['电影类型'].apply(lambda x: set(x.split(',')))  # 处理电影类型
for category in all_categories:  # 生成哑变量
    df[category] = df['电影类型'].apply(lambda x: 1 if category in x else 0)

all_countries = set(','.join(df['出品国家']).split(','))  # 找到出品国家的全集
df['出品国家'] = df['出品国家'].apply(lambda x: set(x.split(',')))  # 处理出品国家
for country in all_countries:  # 生成哑变量
    df[country] = df['出品国家'].apply(lambda x: 1 if country in x else 0)

movie_data = df
movie_data['电影名称长度'] = movie_data['电影名称'].apply(len)  # 添加电影名称长度

x = df.drop(['电影类型', '电影名称', '出品国家', '累计票房'], axis=1)
y = movie_data['累计票房']
X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=123)

err_test = []
err_train = []
K = np.arange(1, 50, 5)
for D in K:
    classifier = RandomForestRegressor(n_estimators=D, random_state=123)  # 设定随机森林分类器的模型参数
    classifier.fit(X_train, y_train)
    err_test.append(1 - classifier.score(X_test, y_test))
    err_train.append(1 - classifier.score(X_train, y_train))
    print(D)
best_D = K[err_test.index(np.min(err_test))]

model = RandomForestRegressor(n_estimators=best_D, random_state=123)
model.fit(X_train, y_train)

# fig = plt.figure(figsize=(20, 8))
# plt.grid(True, linestyle='-.')
# plt.plot(K, err_test, label="测试误差", linestyle='-')
# plt.plot(K, err_train, label="训练误差", linestyle='-')
# plt.title('随机森林的拟合优度%.9f(最优参数K=%d)' % ((1 - err_test[err_test.index(np.min(err_test))]), best_D),
#           fontsize=14)
# plt.xlabel("depth", fontsize=14)
# plt.ylabel("误差（1-R方）", fontsize=14)
# plt.legend(fontsize=12)
# plt.legend()
# plt.show()

feature_importances = model.feature_importances_
print("特征重要性:", feature_importances)
# base_estimators = model.estimators_
# print("基础决策树列表:", base_estimators)
r2_score = model.score(X_test, y_test)
print("模型在测试集上的R²得分:", r2_score)
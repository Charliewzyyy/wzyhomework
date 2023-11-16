import os
import sys
import click

from flask import Flask, render_template
from flask import request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy  # 导入扩展类
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import login_user
from flask_login import login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

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


class Movie(db.Model):  # 表名将会是 movie
    id = db.Column(db.Integer, primary_key=True)  # 主键
    title = db.Column(db.String(60))  # 电影标题
    year = db.Column(db.String(4))  # 电影年份


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

    # 全局的两个变量移动到这个函数内
    name = 'Charliewzyyy'
    movies = [
        {'title': 'My Neighbor Totoro', 'year': '1988'},
        {'title': 'Dead Poets Society', 'year': '1989'},
        {'title': 'A Perfect World', 'year': '1993'},
        {'title': 'Leon', 'year': '1994'},
        {'title': 'Mahjong', 'year': '1996'},
        {'title': 'Swallowtail Butterfly', 'year': '1996'},
        {'title': 'King of Comedy', 'year': '1999'},
        {'title': 'Devils on the Doorstep', 'year': '1999'},
        {'title': 'WALL-E', 'year': '2008'},
        {'title': 'The Pork of Music', 'year': '2012'},
    ]

    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(title=m['title'], year=m['year'])
        db.session.add(movie)

    db.session.commit()
    click.echo('Done.')


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

    if request.method == 'POST':  # 处理编辑表单的提交请求
        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.')
            return redirect(url_for('edit', movie_id=movie_id))
            # 重定向回对应的编辑页面

        movie.title = title  # 更新标题
        movie.year = year  # 更新年份
        db.session.commit()  # 提交数据库会话
        flash('Item updated.')
        return redirect(url_for('index'))  # 重定向回主页

    return render_template('edit.html', movie=movie)  # 传入被编辑的电影记录


### 删除电影条目
@app.route('/movie/delete/<int:movie_id>', methods=['POST'])  # 限定只接受 POST 请求
@login_required  # 登录保护
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)  # 获取电影记录
    db.session.delete(movie)  # 删除对应的记录
    db.session.commit()  # 提交数据库会话
    flash('Item deleted.')
    return redirect(url_for('index'))  # 重定向回主页


### 程序主页
### 在主页视图读取数据库记录
@app.route('/', methods=['GET', 'POST'])  # 同时接受GET和POST请求
def index():
    ### 创建电影条目
    if request.method == 'POST':  # 判断是否是 POST 请求
        if not current_user.is_authenticated:  # 仅需要禁止未登录用户创建新条目
            return redirect(url_for('index'))  # 重定向到主页

        # 获取表单数据
        title = request.form.get('title')  # 传入表单对应输入字段的name值
        year = request.form.get('year')
        # 验证数据
        if not title or not year or len(year) > 4 or len(title) > 60:
            flash('Invalid input.')  # 显示错误提示
            return redirect(url_for('index'))  # 重定向回主页
        # 保存表单数据到数据库
        movie = Movie(title=title, year=year)  # 创建记录
        db.session.add(movie)  # 添加到数据库会话
        db.session.commit()  # 提交数据库会话
        flash('Item created.')  # 显示成功创建的提示
        return redirect(url_for('index'))  # 重定向回主页

    # user = User.query.first()  # 读取用户记录 # 有inject_user()了，就可以不用了
    movies = Movie.query.all()  # 读取所有电影记录
    # return render_template('index.html', user=user, movies=movies)
    return render_template('index.html', movies=movies)


### 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # request.form 是一个类似字典的对象
        password = request.form['password']

        if not username or not password:  # 检查用户名和密码是否为空
            flash('Invalid input.')
            return redirect(url_for('login'))

        user = User.query.first()

        # 验证用户名和密码是否一致
        if username == user.username and user.validate_password(password):
            login_user(user)  # 登入用户
            flash('Login success.')
            return redirect(url_for('index'))  # 重定向到主页

        flash('Invalid username or password.')  # 如果验证失败，显示错误消息
        return redirect(url_for('login'))  # 重定向回登录页面

    return render_template('login.html')  # # 渲染并返回登录页面的 HTML 模板


### 登出
@app.route('/logout')
@login_required  # 用于视图保护，后面会详细介绍
def logout():
    logout_user()  # 登出用户
    flash('Goodbye.')
    return redirect(url_for('index'))  # 重定向回首页


### 支持设置用户名字
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']  # 从表单中获取输入的新名称

        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))

        # current_user.name = name  # 将当前登录用户的名称更新为新输入的名称
        # current_user 会返回当前登录用户的数据库记录对象
        # 等同于下面的用法
        user = User.query.first()
        user.name = name
        db.session.commit()  # 提交数据库会话，保存更改
        flash('Settings updated.')   # 通过 Flash 提示用户设置已更新
        return redirect(url_for('index'))  # 重定向到主页

    return render_template('settings.html')  # 渲染并返回设置页面的 HTML 模板

# ### 定义虚拟数据
# name = 'Charliewzyyy'
# movies = [
#     {'title': 'My Neighbor Totoro', 'year': '1988'},
#     {'title': 'Dead Poets Society', 'year': '1989'},
#     {'title': 'A Perfect World', 'year': '1993'},
#     {'title': 'Leon', 'year': '1994'},
#     {'title': 'Mahjong', 'year': '1996'},
#     {'title': 'Swallowtail Butterfly', 'year': '1996'},
#     {'title': 'King of Comedy', 'year': '1999'},
#     {'title': 'Devils on the Doorstep', 'year': '1999'},
#     {'title': 'WALL-E', 'year': '2008'},
#     {'title': 'The Pork of Music', 'year': '2012'},
# ]

# @app.route('/')
# def hello():
#     return '<h1>Hello Totoro!</h1><img src="http://helloflask.com/totoro.gif">'
#
#
# @app.route("/user/<name>")
# def user_page(name):
#     return "User: %s" % name
#
#
# @app.route('/test')
# def test_url_for():
#     # 下面是一些调用示例（请在命令行窗口查看输出的 URL）：
#     print(url_for('hello'))  # 输出：/
#     # 注意下面两个调用是如何生成包含 URL 变量的 URL 的
#     print(url_for('user_page', name='greyli'))  # 输出：/user/greyli
#     print(url_for('user_page', name='peter'))  # 输出：/user/peter
#     print(url_for('test_url_for'))  # 输出：/test
#     # 下面这个调用传入了多余的关键字参数，它们会被作为查询字符串附加到 URL后面。
#     print(url_for('test_url_for', num=2))  # 输出：/test?num=2
#     return 'Test page'

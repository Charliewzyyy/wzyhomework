import unittest
from flask import current_app
from app import app, db, Movie, User, forge, initdb


# from wzyhomework import app, db
# from wzyhomework.models import Movie, User
# from wzyhomework.commands import forge, initdb

class WatchlistTestCase(unittest.TestCase):
    def setUp(self):
        # 更新配置
        app.config.update(
            TESTING=True,  # 开启测试模式，这样在出错时不会输出多余信息
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:'  # 使用 SQLite 内存型数据库
        )
        # 创建应用上下文
        with app.app_context():
            # 创建数据库和表
            db.create_all()

            # 创建测试数据，一个用户，一个电影条目
            user = User(name='Test', username='test')
            user.set_password('123')
            movie = Movie(title='Test Movie Title', year='2019')

            # 使用 add_all() 方法一次添加多个模型类实例，传入列表
            db.session.add_all([user, movie])
            db.session.commit()

            self.client = app.test_client()  # 创建测试客户端
            self.runner = app.test_cli_runner()  # 创建测试命令运行器
            self.client.get('/logout', follow_redirects=True)

    def tearDown(self):
        # 清除应用上下文
        with app.app_context():
            db.session.remove()  # 清除数据库会话
            db.drop_all()  # 删除数据库表

        # self.app_context.pop()

    # 测试程序实例是否存在
    def test_app_exist(self):
        self.assertIsNotNone(app)
        # 测试程序是否处于测试模式

    def test_app_is_testing(self):
        self.assertTrue(app.config['TESTING'])

    # 测试 404 页面
    def test_404_page(self):
        response = self.client.get('/nothing')  # 传入目标 URL

        # 从响应对象中获取返回的数据。as_text=True 表示将二进制数据解码为文本
        data = response.get_data(as_text=True)
        self.assertIn('Page Not Found - 404', data)  # 确保返回的页面包含这个字符串
        self.assertIn('返回首页', data)
        self.assertEqual(response.status_code, 404)  # 判断响应状态码为 404

    # 测试主页
    def test_index_page(self):
        response = self.client.get('/')

        data = response.get_data(as_text=True)
        self.assertIn('Test的电影管理系统', data)
        self.assertEqual(response.status_code, 200)  # 检查服务器是否正确响应主页请求

    # 辅助方法，用于登入用户
    def login(self):
        self.client.post('/login', data=dict(  # 发送提交登录表单的 POST 请求
            username='test',
            password='123'
        ), follow_redirects=True)  # 可以跟随重定向，最终返回的会是重定向后的响应

    # 测试更新条目
    def test_update_item(self):
        self.login()

        # 测试更新页面
        response = self.client.get('/movie/edit/1')
        data = response.get_data(as_text=True)
        self.assertIn('编辑电影信息', data)
        self.assertIn('Test Movie Title', data)
        self.assertIn('2019', data)

    # 测试删除条目
    def test_delete_item(self):
        self.login()

        response = self.client.post('/movie/delete/1', follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('电影条目成功删除~', data)
        self.assertNotIn('Test Movie Title', data)

    # 测试登录保护
    def test_login_protect(self):
        response = self.client.get('/')
        data = response.get_data(as_text=True)
        self.assertNotIn('Logout', data)
        self.assertNotIn('Settings', data)
        self.assertNotIn('<form method="post">', data)
        self.assertNotIn('Delete', data)
        self.assertNotIn('Edit', data)

    # 测试登录
    def test_login(self):
        response = self.client.post('/login', data=dict(
            username='test',
            password='123'
        ), follow_redirects=True)

        data = response.get_data(as_text=True)
        self.assertIn('成功登录~', data)

        self.assertIn('用户中心', data)
        self.assertIn('删除', data)
        self.assertIn('编辑', data)

        # 测试使用错误的密码登录
        response = self.client.post('/login', data=dict(
            username='test',
            password='456'
        ), follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertNotIn('Login success.', data)
        self.assertIn('用户名或密码输入错误！', data)

        # 测试使用错误的用户名登录
        response = self.client.post('/login', data=dict(
            username='wrong',
            password='123'
        ), follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertNotIn('Login success.', data)
        self.assertIn('用户名或密码输入错误！', data)

        # 测试使用空用户名登录
        response = self.client.post('/login', data=dict(
            username='',
            password='123'
        ), follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertNotIn('Login success.', data)
        self.assertIn('输入错误！', data)

        # 测试使用空密码登录
        response = self.client.post('/login', data=dict(
            username='test',
            password=''
        ), follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertNotIn('Login success.', data)
        self.assertIn('输入错误！', data)

    # 测试登出
    def test_logout(self):
        self.login()

        response = self.client.get('/logout', follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('再见~', data)
        self.assertNotIn('Logout', data)
        self.assertNotIn('Settings', data)
        self.assertNotIn('Delete', data)
        self.assertNotIn('Edit', data)
        self.assertNotIn('<form method="post">', data)

    # 测试设置
    def test_settings(self):
        self.login()

        # 测试设置页面
        response = self.client.get('/settings')
        data = response.get_data(as_text=True)
        self.assertIn('用户中心', data)

        # 测试更新设置
        response = self.client.post('/settings', data=dict(
            name='Grey Li',
        ), follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('用户名成功更新~', data)
        self.assertIn('Grey Li', data)

        # 测试更新设置，名称为空
        response = self.client.post('/settings', data=dict(
            name='',
        ), follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertNotIn('Settings updated.', data)
        self.assertIn('输入错误！', data)

    # 测试虚拟数据
    def test_forge_command(self):
        with app.app_context():
            result = self.runner.invoke(forge)  # 运行forge命令
            self.assertIn('Done.', result.output)
            self.assertNotEqual(Movie.query.count(), 0)  # 确保Movie数据库表中有数据

    # 测试初始化数据库
    def test_initdb_command(self):
        result = self.runner.invoke(initdb)
        self.assertIn('Initialized database.', result.output)

    # 测试生成管理员账户
    def test_admin_command(self):
        with app.app_context():
            db.drop_all()
            db.create_all()
            result = self.runner.invoke(args=['admin', '--username', 'grey', '--password', '123'])
            self.assertIn('Creating user...', result.output)
            self.assertIn('Done.', result.output)
            self.assertEqual(User.query.count(), 1)
            self.assertEqual(User.query.first().username, 'grey')
            self.assertTrue(User.query.first().validate_password('123'))

    # 测试更新管理员账户
    def test_admin_command_update(self):
        with app.app_context():
            # 使用 args 参数给出完整的命令参数列表
            result = self.runner.invoke(args=['admin', '--username', 'peter', '--password', '456'])
            self.assertIn('Updating user...', result.output)  # 输出中包含'Updating user...'字符串。
            self.assertIn('Done.', result.output)
            self.assertEqual(User.query.count(), 1)
            self.assertEqual(User.query.first().username, 'peter')
            self.assertTrue(User.query.first().validate_password('456'))


if __name__ == '__main__':
    unittest.main()  # 会执行所有以test_开头的测试方法，并报告测试结果

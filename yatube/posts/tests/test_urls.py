from http import HTTPStatus

from django.test import Client, TestCase

from posts.models import Group, Post, User, Follow


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.follower = User.objects.create_user(username='follower')
        cls.follow = Follow.objects.create(
            user=cls.follower,
            author=cls.author
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group
        )
        cls.private_reference = {
            f'/posts/{PostURLTests.post.id}/edit/': (('posts/create_post.html',
                                                      HTTPStatus.OK)),
            '/create/': ('posts/create_post.html', HTTPStatus.OK),

            '/follow/': ('posts/follow.html', HTTPStatus.OK),
        }

        cls.another_private_reference = {
            f'/profile/{PostURLTests.post.author}/follow/': (
                ('posts/profile.html', HTTPStatus.FOUND)),

            f'/profile/{PostURLTests.post.author}/unfollow/': (
                ('posts/profile.html', HTTPStatus.FOUND)),
            f'/posts/{PostURLTests.post.id}/comment/': (
                ('posts/post_detail.html', HTTPStatus.FOUND)),
        }

        cls.public_reference = {
            '/': ('posts/index.html', HTTPStatus.OK),
            f'/group/{PostURLTests.group.slug}/': (('posts/group_list.html',
                                                    HTTPStatus.OK)),
            f'/profile/{PostURLTests.post.author}/': (('posts/profile.html',
                                                       HTTPStatus.OK)),
            f'/posts/{PostURLTests.post.id}/': (('posts/post_detail.html',
                                                HTTPStatus.OK)),
            '/page_not_found/': ('core/404.html', HTTPStatus.NOT_FOUND)
        }

    def setUp(self):
        # Неавторизованый пользователь
        self.guest_client = Client()
        # Авторизованый автор
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)

    def test_another_private_url_use_correct_templates(self):
        """Проверка доступности URL адресов"""
        for url, status in PostURLTests.another_private_reference.items():
            response = self.authorized_author.get(url)
            with self.subTest(url=url):
                self.assertEqual(response.status_code, status[1])

    def test_another_private_url_use_correct_templates(self):
        """Проверка доступности шаблонов"""
        for url, templates in PostURLTests.another_private_reference.items():
            response = self.authorized_follower.get(url, follow=True)
            with self.subTest(url=url):
                self.assertTemplateUsed(response, templates[0])

    def test_public_templates_url_at_desired_location(self):
        """Проверка доступности URL адресов для любого пользователя"""
        for url, status in PostURLTests.public_reference.items():
            response = self.guest_client.get(url)
            with self.subTest(url=url):
                self.assertEqual(response.status_code, status[1])

    def test_public_templates_url_usses_correct_template(self):
        """Проверка доступности шаблонов для любого пользователя """
        for url, templates in PostURLTests.public_reference.items():
            response = self.guest_client.get(url)
            with self.subTest(url=url):
                self.assertTemplateUsed(response, templates[0])

    def test_private_templates_url_at_desired_location(self):
        """Проверка доступности URL адресов для авторизованого пользователя"""
        for url, status in PostURLTests.private_reference.items():
            response = self.authorized_author.get(url)
            with self.subTest(url=url):
                self.assertEqual(response.status_code, status[1])

    def test_private_templates_url_usses_correct_template(self):
        """Проверка доступности шаблонов для авторизованого пользователя """
        for url, templates in PostURLTests.private_reference.items():
            response = self.authorized_author.get(url)
            with self.subTest(url=url):
                self.assertTemplateUsed(response, templates[0])

    def test_404_page_is_working(self):
        """Проверка запроса к несуществующей страницы"""
        response = self.guest_client.get('/page_not_found/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

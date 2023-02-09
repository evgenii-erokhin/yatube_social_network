import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post, User, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

TEST_PAG_3 = 3


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы'
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
            image=uploaded
        )
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            post=cls.post,
            author=cls.user,
        )
        cls.private_reference = {
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': PostPagesTest.post.id}):
                   ('posts/create_post.html'),
        }
        cls.public_reference = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': f'{PostPagesTest.group.slug}'}):
                   ('posts/group_list.html'),
            reverse('posts:profile',
                    kwargs={'username': f'{PostPagesTest.author}'}):
                   ('posts/profile.html'),
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in PostPagesTest.public_reference.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_public_views_show_correct_context(self):
        """Проверка, что вью функции для общедоступных страниц
           передают корректный контекст"""
        for revers_name in PostPagesTest.public_reference.keys():
            with self.subTest(revers_name=revers_name):
                response = self.guest_client.get(revers_name)
                for post in response.context['page_obj']:
                    self.assertIsInstance(post, Post)

                first_post = response.context['page_obj'][0]
                self.assertEqual(first_post.text, PostPagesTest.post.text)
                self.assertEqual(first_post.group, PostPagesTest.post.group)
                self.assertEqual(first_post.author, PostPagesTest.post.author)
                self.assertEqual(first_post.image, PostPagesTest.post.image)

    def test_pfivate_views_show_correct_context(self):
        """Проверка, что вью функции для приватных старниц
        передают правильный контекст"""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for revers_name in PostPagesTest.private_reference.keys():
            with self.subTest(revers_name=revers_name):
                response = self.authorized_client.get(revers_name)
                for field, type in form_fields.items():
                    with self.subTest(field=field):
                        form_field = (response.context.get('form').
                                      fields.get(field))
                        self.assertIsInstance(form_field, type)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post detailt сформирован с правильным контекстом."""
        response = (self.authorized_client.
                    get(reverse('posts:post_detail',
                        kwargs={'post_id': f'{PostPagesTest.post.id}'})))
        self.assertEqual(response.context.get('posts').image,
                         PostPagesTest.post.image)
        self.assertEqual(response.context.get('posts').text,
                         PostPagesTest.post.text)

    def test_post_show_correct(self):
        """Проверка, что созданый пост появляется
           на нужных страницах"""
        for page in PostPagesTest.public_reference.keys():
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertIn(PostPagesTest.post, response.context['page_obj'])

    def test_cache_correct_working(self):
        """Тест кеша, сохраняет контент и обновляет его каждые 20 секунд"""
        index_before = self.guest_client.get(reverse('posts:index')).content
        Post.objects.all().delete()
        index_affter = self.guest_client.get(reverse('posts:index')).content
        self.assertEqual(index_before, index_affter)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание группы'
        )

        for i in range(settings.NUM_OF_POSTS + TEST_PAG_3):
            Post.objects.create(
                text='Тестовый текст поста',
                author=cls.author,
                group=cls.group
            )

        cls.paginator_page = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={
                'slug': PaginatorViewsTest.group.slug}),
            reverse('posts:profile', kwargs={
                'username': PaginatorViewsTest.author.username})
        )

    def test_pagenator_at_the_views(self):
        """Тестирование паджинатора"""
        for revers_name in PaginatorViewsTest.paginator_page:
            with self.subTest(revers_name=revers_name):
                response = self.authorized_client.get(revers_name)
                self.assertEqual(len(response.context['page_obj']),
                                 settings.NUM_OF_POSTS)
                response = self.authorized_client.get(revers_name + '?page=2')
                self.assertEqual(len(response.context['page_obj']), TEST_PAG_3)


class FollowOnProfile(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.follower = User.objects.create_user(username='follower')
        cls.notfollower = User.objects.create_user(username='notfollower')

        cls.follow = Follow.objects.create(user=cls.follower,
                                           author=cls.author)
        cls.post = Post.objects.create(
            text='Ещё один пост на тест',
            author=cls.author
        )

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.non_author_client = Client()
        self.non_author_client.force_login(self.follower)
        self.not_follower_client = Client()
        self.not_follower_client.force_login(self.notfollower)

    def test_follow_view_correct_works(self):
        """Тест на подписку автора"""
        self.non_author_client.get(
            reverse('posts:profile',
                    kwargs={'username': FollowOnProfile.author}))
        self.assertTrue(Follow.objects.filter(user=FollowOnProfile.follower,
                        author=FollowOnProfile.author).exists())

    def test_follower_can_see_posts_authors(self):
        """Подписчик может просматривать посты автора на которого подписался"""
        new_post = Post.objects.create(
            author=FollowOnProfile.author,
            text='Новый пост, для подписчиков'
        )
        Follow.objects.create(
            user=FollowOnProfile.follower,
            author=FollowOnProfile.author
        )
        response = self.non_author_client.get(
            reverse('posts:follow_index')
        )
        post_follower = response.context['page_obj'][0]
        self.assertEqual(post_follower.text, new_post.text)

    def test_not_follower_cant_see_posts_at_follow_index(self):
        """Не подписчик не видит посты на follow.index"""
        new_post_for_follower = Post.objects.create(
            author=FollowOnProfile.author,
            text='Новый пост, для подписчиков'
        )
        Follow.objects.create(
            user=FollowOnProfile.follower,
            author=FollowOnProfile.author
        )
        response = self.not_follower_client.get(reverse('posts:follow_index'))
        post_not_follower = response.context['page_obj']
        self.assertNotIn(new_post_for_follower, post_not_follower)

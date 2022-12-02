from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from posts.models import Post, Group

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        # Создадим запись в БД для проверки доступности адреса task/test-slug/
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='test-username')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author = Client()
        self.author.force_login(user=PostsURLTests.post.author)

    def test_urls_uses_correct_template_not_auth_client(self):
        """
        URL-адрес использует соответствующий шаблон
        для неавторизованных пользователей.
        """
        # Шаблоны по адресам
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_correct_template_author(self):
        """URL-адрес использует соответствующий шаблон для автора статьи."""
        responce = self.author.get('/posts/1/edit/')
        self.assertTemplateUsed(responce, 'posts/create_post.html')

    def test_urls_uses_correct_template_auth_client(self):
        """
        URL-адрес использует соответствующий шаблон
        для авторизованных пользователей.
        """
        response = self.authorized_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_urls_uses_uncorrect_template(self):
        """
        Некорректный URL-адрес вызывает ошибку 404
        и вызывает кастомный шаблон.
        """
        response = self.guest_client.get('/unexiting_page/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')

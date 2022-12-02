from posts.models import Post, Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from posts.forms import PostForm
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
from django.conf import settings
import shutil
from django.core.cache import cache

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.imaging = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.uploaded = SimpleUploadedFile(
            name="small.gif",
            content=cls.imaging,
            content_type="image/gif"
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            image=cls.uploaded
        )
        cls.form = PostForm()

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(user=PostFormsTest.post.author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        cache.clear()

    def test_create_post(self):
        """Валидная форма создает запись в create_post."""
        post_count = Post.objects.count()

        form_data = {
            'text': 'Тестовый тест 2',
            'group': '',
            'image': self.post.image
        }
        # Отправляем POST-запрос
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:profile',
                                     kwargs={'username': 'auth'}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый тест 2',
            ).exists()
        )

    def test_edit_post(self):
        """Валидная форма редактирует пост по пути posts:post_edit."""
        form_data = {
            'text': 'Тестовый тест 3',
            'group': '',
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(1,)),
            data=form_data,
            follow=True
        )
        post_count = Post.objects.count()
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': 1}))
        self.assertEqual(Post.objects.count(), post_count)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый тест 3',
            ).exists()
        )

    def test_guest_client_cannot_create_post(self):
        """Неавторизованный клиент не может создать пост."""
        form_data = {
            'text': 'Тестовый тест 3',
            'group': '',
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_guest_client_cannot_edit_post(self):
        """Неавторизованный клиент не может редактировать пост."""
        form_data = {
            'text': 'Тестовый тест 3',
            'group': '',
        }
        response = self.guest_client.post(
            reverse('posts:post_edit', args=(1,)),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')

    def test_auth_not_author_post_cannot_edit_post(self):
        form_data = {
            'text': 'Тестовый тест 3',
            'group': '',
        }
        response = self.guest_client.post(
            reverse('posts:post_edit', args=(1,)),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')

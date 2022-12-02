from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Post, Group, Comment, Follow
from django import forms
import tempfile
from django.conf import settings
import shutil
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

User = get_user_model()
TEST_NUM = 10


class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            author=cls.user
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostViewsTest.post.author)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.post.author}
                    ): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.pk}
                    ): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk}
                    ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        excepted_object = list(Post.objects.all()[:TEST_NUM])
        self.assertEqual(list(response.context['page_obj']), excepted_object)

    def test_index_page_pagination(self):
        """Тест главной страницы с правильной пагинацией."""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        responce = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        excepted = list(Post.objects.filter(
                        group_id=self.group.id)[:TEST_NUM])
        self.assertEqual(list(responce.context['page_obj']), excepted)

    def test_group_page_pagination(self):
        """Тест страницы группы с правильной пагинацией."""
        response = self.guest_client.get(reverse('posts:group_list',
                                         kwargs={'slug': self.group.slug}))
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': self.post.author}))
        excepted = list(Post.objects.filter(author_id=self.user.id)[:TEST_NUM])
        self.assertEqual(list(response.context['page_obj']), excepted)

    def test_profile_page_pagination(self):
        """Тест страницы профиля с правильной пагинацией."""
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': self.post.author}))
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        responce = self.guest_client.get(reverse('posts:post_detail',
                                                 kwargs={'post_id': 1}))
        self.assertEqual(responce.context.get('post').text, self.post.text)
        self.assertEqual(responce.context.get('post').author, self.post.author)
        self.assertEqual(responce.context.get('post').group, self.post.group)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_create edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_edit',
                                                      kwargs={'post_id': 1}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_check_group(self):
        """
        Проверка создания поста с выбранной группой на главной странице,
        на странице группы и странице профиля.
        """
        form_fields = {
            reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertNotIn(expected, form_field)

    def test_check_group_in_pages(self):
        """Проверка группы на правильное распредение по шаблонам"""
        form_fields = {
            reverse('posts:index'): Post.objects.get(group=self.post.group),
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): (
                        Post.objects.get(group=self.post.group)),
            reverse('posts:profile',
                    kwargs={'username': self.post.author}): (
                        Post.objects.get(group=self.post.group)),
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_commets_only_auth(self):
        """Оставлять комментарий может только авторизованный пользователь."""
        comments = Comment.objects.all().count()
        form_data = {
            'text': 'Тестовый комментарий 2'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': self.post.pk}))
        self.assertEqual(Comment.objects.all().count(), comments + 1)
        self.assertTrue(Comment.objects.filter(
            text='Тестовый комментарий 2').exists())

        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/posts/1/comment/')

    def test_cashe(self):
        """Проверка кеша."""
        response_1 = self.guest_client.get(reverse('posts:index'))
        obj_1 = response_1.content
        Post.objects.get(pk=1).delete()
        response_2 = self.guest_client.get(reverse('posts:index'))
        obj_2 = response_2.content
        self.assertEqual(obj_1, obj_2)

    def test_follow_psge(self):
        """Проверка страницы подписок."""
        # Проверяем, что подписок нет
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)

        # Проверка подписки на автора
        Follow.objects.get_or_create(user=self.user, author=self.post.author)
        response_2 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response_2.context['page_obj']), 1)

        # Проверка, что пост не появился у неподписанных пользователей
        no_name = User.objects.create(username='no_name')
        self.authorized_client.force_login(no_name)
        response_3 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post, response_3.context['page_obj'])

        # Проверка отписки от автора поста
        Follow.objects.all().delete()
        response_4 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response_4.context['page_obj']), 0)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostImageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='admin')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
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
            text="Тестовый текст",
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        cache.clear()

    def setUp(self):
        self.guest_client = Client()
        self.auth_client = Client()
        self.auth_client.force_login(self.post.author)

    def test_image_in_group_list_page(self):
        """Изображение передается на страницу группы."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        )
        obj = response.context['page_obj'][0]
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_index_and_profile_page(self):
        """Изображение передается на главную страницу, а также профайла."""
        templates = (
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.post.author}),
        )
        for url in templates:
            with self.subTest(url):
                response = self.guest_client.get(url)
                object = response.context['page_obj'][0]
                self.assertEqual(object.image, self.post.image)

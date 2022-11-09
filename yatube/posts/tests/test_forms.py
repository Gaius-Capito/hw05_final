import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, User


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group_1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='group_1'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='group_2'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            group=cls.group_1)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_create_post_form(self):
        """Создание поста и редирект в профиль автора"""
        posts_count = Post.objects.count()
        self.assertEqual(posts_count, 1, 'Количество постов > 1')
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
        form_data = {
            'text': 'Текст',
            'group': self.group_1.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(
            Post.objects.all().count(),
            posts_count + 1,
            'Пост не сохранен'
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', args=(self.author.username,)),
        )
        post = Post.objects.first()
        self.assertEqual(
            post.text,
            form_data['text'],
            'Несоответствие текста поста'
        )
        self.assertEqual(post.author, self.author, 'Несоответствие автора')
        self.assertEqual(
            post.group.pk,
            form_data['group'],
            'Несоответствие группы'
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_edit_post_form(self):
        """Изменение поста после редактирования и редирект на карточку поста"""
        posts_count = Post.objects.count()
        self.assertEqual(posts_count, 1, 'Количество постов > 1')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small_2.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Отредактированный текст',
            'group': self.group_2.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        modified_post = Post.objects.first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=(self.post.pk,))
        )
        self.assertEqual(
            modified_post.text,
            form_data['text'],
            'Текст не отредактирован!'
        )
        self.assertEqual(
            modified_post.group.pk,
            form_data['group'],
            'Группа не изменилась!'
        )
        self.assertEqual(modified_post.author, self.post.author)
        self.assertEqual(
            Post.objects.count(),
            posts_count,
            'Изменилось кол-во постов'
        )
        response = self.authorized_client.post(
            reverse('posts:group_list', args=(self.group_1.slug,))
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            len(response.context['page_obj']),
            settings.NUMS_POSTS_AFTER_EDIT_ZERO)

    def test_guest_user_cannot_edit_post(self):
        """Редактирование записи не авторизованным пользователем"""
        posts_count = Post.objects.count()
        self.assertEqual(posts_count, 1, 'Количество постов > 1')
        form_data = {
            'text': 'Запись не должна измениться',
            'group': self.group_2.pk
        }
        response = self.client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        not_modified_post = Post.objects.first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(
            not_modified_post.text,
            form_data['text'],
            'Текст отредактирован!'
        )
        self.assertNotEqual(
            not_modified_post.group,
            form_data['group'],
            'Группа изменилась!'
        )
        self.assertEqual(
            Post.objects.count(),
            posts_count,
            'Изменилось кол-во постов'
        )

    def test_guest_cant_create_post(self):
        """Создание поста анонимным пользователем."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста, написанный гостем',
            'group': self.group_1.pk,
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post = Post.objects.first()
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )
        self.assertNotEqual(post.text, form_data['text'])
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), post_count)


class CommentFormsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовая пост',
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_auth_user_can_write_comment(self):
        """Комментарии могут оставлять авторизованные пользователи"""
        comments_count = self.post.comments.count()
        form_data = {
            'text': 'Новый комментарий',
            'author': self.author
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.id,)),
            data=form_data,
            follow=True,
        )
        self.assertEqual(Post.objects.count(), comments_count + 1)
        self.assertTrue(
            self.post.comments.filter(
                text='Новый комментарий',
                author=self.author
            ).exists()
        )
        comment = response.context["comments"][0]
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author, self.author)
        self.assertEqual(comment.text, form_data["text"])

    def test_guest_cannot_write_comment(self):
        """Комментарии не могут оставлять гости"""
        comments_count = self.post.comments.count()
        form_data = {
            'text': 'Новый комментарий',
            'author': self.author
        }
        self.client.post(
            reverse('posts:add_comment', args=(self.post.id,)),
            data=form_data,
            follow=True,
        )
        self.assertEqual(self.post.comments.count(), comments_count)

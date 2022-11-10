from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
        )
        cls.urls = (
            ('posts:index', None, '/',),
            ('posts:post_create', None, '/create/'),
            ('posts:profile', (cls.author.username,),
             f'/profile/{cls.author.username}/'),
            ('posts:post_detail', (cls.post.pk,),
             f'/posts/{cls.post.pk}/'),
            ('posts:group_list', (cls.group.slug,),
             f'/group/{cls.group.slug}/'),
            ('posts:post_edit', (cls.post.pk,),
             f'/posts/{cls.post.pk}/edit/'),
            ('posts:add_comment', (cls.post.pk,),
             f'/posts/{cls.post.pk}/comment/'),
            ('posts:follow_index', None, '/follow/'),
            ('posts:profile_follow', (cls.author,),
             f'/profile/{cls.author}/follow/'),
            ('posts:profile_unfollow', (cls.author,),
             f'/profile/{cls.author}/unfollow/'),
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_author = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author.force_login(self.author)

    def test_url_connected_to_reverse(self):
        """reverse соответствует url"""
        for name, arg, url in self.urls:
            with self.subTest(name=name, arg=arg):
                self.assertEqual(reverse(name, args=arg), url)

    def test_post_edit_url_for_author(self):
        """ Проверка доступности url автору"""
        redirect_names_profile = [
            'posts:profile_follow',
            'posts:profile_unfollow'
        ]
        for name, arg, url in self.urls:
            with self.subTest(name=name, arg=arg):
                response = self.authorized_author.get(reverse(name, args=arg))
                if name == 'posts:add_comment':
                    self.assertRedirects(
                        response,
                        reverse('posts:post_detail', args=(self.post.pk,))
                    )
                elif name in redirect_names_profile:
                    self.assertRedirects(
                        response,
                        reverse('posts:profile', args=(self.author,))
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_detail_url_exists_at_desired_location_authorized(self):
        """Проверка доступности адресов для авторизованного
        пользователя."""
        redirect_names_posts = [
            'posts:post_edit',
            'posts:add_comment'

        ]
        redirect_names_profile = [
            'posts:profile_follow',
            'posts:profile_unfollow'
        ]
        for name, arg, url in self.urls:
            with self.subTest(name=name, arg=arg):
                response = self.authorized_client.get(reverse(name, args=arg))
                if name in redirect_names_posts:
                    self.assertRedirects(
                        response,
                        reverse('posts:post_detail', args=(self.post.pk,))
                    )
                elif name in redirect_names_profile:
                    self.assertRedirects(
                        response,
                        reverse('posts:profile', args=(self.author,))
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_added_url_exists_at_desired_location(self):
        """Проверка доступности адресов для всех пользователей."""
        address_names_login = [
            'posts:post_edit',
            'posts:post_create',
            'posts:add_comment',
            'posts:follow_index',
            'posts:profile_follow',
            'posts:profile_unfollow',
        ]
        for name, arg, url in self.urls:
            with self.subTest(name=name, arg=arg):
                response = self.client.get(reverse(name, args=arg))
                if name in address_names_login:
                    self.assertRedirects(
                        response,
                        reverse('users:login') + f'?next={url}'
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_uses_correct_templates(self):
        """"URL-адрес использует соответствующий шаблон."""
        templates = (
            ('posts:index', None, 'posts/index.html',),
            ('posts:post_create', None, 'posts/create_post.html'),
            ('posts:profile', (self.user.username,), 'posts/profile.html'),
            ('posts:post_detail', (self.post.pk,), 'posts/post_detail.html'),
            ('posts:group_list', (self.group.slug,), 'posts/group_list.html'),
            ('posts:post_edit', (self.post.pk,), 'posts/create_post.html'),
            ('posts:follow_index', None, 'posts/follow.html')
        )
        for name, arg, template in templates:
            with self.subTest(name=name, arg=arg):
                response = self.authorized_author.get(reverse(name, args=arg))
                self.assertTemplateUsed(response, template)

    def test_nonexistent_page_url(self):
        """Несуществующая страница вернет ошибку 404"""
        response = self.client.get('/nonexistent_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.authorized_client.get('/nonexistent_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

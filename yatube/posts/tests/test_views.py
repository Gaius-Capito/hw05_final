from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Follow, Group, Post, User


class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.author_2 = User.objects.create_user(username='author_2')
        cls.group = Group.objects.create(
            title='Тестовая группа 1',
            slug='test_slug',
            description='Тестовое описание 1',
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug_2',
            description='Тестовое описание 2',
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
            name='small_2.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
            image=uploaded
        )

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_index_page_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_author.get(reverse('posts:index'))
        self._check_correct_form_from_context(response)

    def test_group_list_page_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_author.get(
            reverse('posts:group_list', args=(self.group.slug,))
        )
        self._check_correct_form_from_context(response)
        group_context = response.context.get('group')
        self.assertEqual(group_context, self.group)

    def test_profile_page_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_author.get(
            reverse('posts:profile', args=(self.author.username,))
        )
        self._check_correct_form_from_context(response)
        author_context = response.context.get('author')
        self.assertEqual(author_context, self.author)

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (
            self.authorized_author.get(
                reverse('posts:post_detail', args=[self.post.pk])
            )
        )
        self._check_correct_form_from_context(response, True)

    def test_post_create_and_edit_correct_context(self):
        """Шаблоны post_create и edit
        сформированы с правильным контекстом."""
        pages = (
            ('posts:post_create', None),
            ('posts:post_edit', (self.post.pk,)),
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for name, arg in pages:
            with self.subTest(name=name):
                response = self.authorized_author.get(reverse(name, args=arg))
                self.assertIn('form', response.context)
                self.assertIsInstance(response.context.get('form'), PostForm)
                for key, field in form_fields.items():
                    with self.subTest(key=key):
                        form_field = response.context.get('form').fields.get(
                            key
                        )
                        self.assertIsInstance(form_field, field)

    def _check_correct_form_from_context(self, response, post_detail=False):
        """Функция для проверки корректного контекста"""
        if post_detail:
            post = response.context.get('post')
        else:
            post = response.context['page_obj'][0]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.author)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.image, self.post.image)

    def test_post_added_correct_group(self):
        """Пост при создании добавлен корректно в правильную группу"""
        post_count = Post.objects.count()
        post_1 = Post.objects.create(
            text='Текст поста',
            author=self.author,
            group=self.group)
        response = self.authorized_author.get(reverse(
            'posts:group_list', args=(self.group_2.slug,))
        )
        response_2 = self.authorized_author.get(reverse(
            'posts:group_list', args=(self.group.slug,))
        )
        self.assertEqual(len(response.context['page_obj']), 0)
        self.assertEqual(post_1.group, self.group)
        self.assertEqual(len(response_2.context['page_obj']), post_count + 1)

    def test_index_page_cache(self):
        """Проверка кеширования index page"""
        first_response = self.authorized_author.get(reverse('posts:index'))
        Post.objects.all().delete()
        second_response = self.authorized_author.get(reverse('posts:index'))
        self.assertEqual(first_response.content, second_response.content)
        cache.clear()
        page_cleared = self.authorized_author.get(reverse('posts:index'))
        self.assertNotEqual(
            first_response,
            page_cleared
        )


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower = User.objects.create_user(username='follower')
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая-группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.posts = [
            Post(
                text=f'Тестовый пост {post}',
                author=cls.author,
                group=cls.group,
            )
            for post in range(settings.NUMS_TEST_POSTS)
        ]
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)
        self.authorized_follower.get(
            reverse(
                'posts:profile_follow',
                args=(self.author,)
            )
        )

    def test_paginator(self):
        """Проверка пагинации"""
        paginator_urls = (
            ('posts:index', None),
            ('posts:group_list', (self.group.slug,)),
            ('posts:profile', (self.author.username,)),
            ('posts:follow_index', None),
        )
        pages = (
            ('?page=1', settings.POSTS_NUMS),
            ('?page=2', int(settings.NUMS_TEST_POSTS)
             - int(settings.POSTS_NUMS))
        )

        for address, args in paginator_urls:
            with self.subTest(address=address):
                for page, nums in pages:
                    with self.subTest(page=page):
                        response = self.authorized_follower.get(
                            reverse(address, args=args) + page
                        )
                        self.assertEqual(
                            len(response.context['page_obj']),
                            nums
                        )


class FollowerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower = User.objects.create_user(username='follower')
        cls.following = User.objects.create_user(username='following')
        cls.post = Post.objects.create(
            author=cls.following,
            text='Тест подписок',
        )

    def setUp(self):
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)
        self.authorized_following = Client()
        self.authorized_following.force_login(self.following)

    def test_follow(self):
        """Проверка работы подписки"""
        count = Follow.objects.count()
        self.authorized_follower.get(
            reverse(
                'posts:profile_follow',
                args=(self.following,)
            )
        )
        count_2 = Follow.objects.count()
        self.assertEqual(count_2, count + 1)
        follow = Follow.objects.first()
        self.assertEqual(follow.author, self.post.author)
        self.assertEqual(follow.user, self.follower)

    def test_unfollow(self):
        """Проверка работы отписки"""
        Follow.objects.create(
            author=self.following,
            user=self.follower,
        )
        count = Follow.objects.count()
        self.authorized_follower.get(
            reverse(
                'posts:profile_unfollow',
                args=(self.following,)
            )
        )
        count_2 = Follow.objects.count()
        self.assertEqual(count_2, count - 1)

    def test_follow_self(self):
        """Нельзя подписаться на самого себя"""
        count = Follow.objects.count()
        self.authorized_following.get(
            reverse(
                'posts:profile_unfollow',
                args=(self.following,)
            )
        )
        self.assertEqual(count, count)

    def test_second_time_follow_impossible(self):
        """Нельзя подписаться на автора второй раз"""
        count = Follow.objects.count()
        follow = self.authorized_follower.get(
            reverse(
                'posts:profile_follow',
                args=(self.following,)
            )
        )
        for _ in range(settings.FOLLOW_NUMS):
            follow
        count_2 = Follow.objects.count()
        self.assertEqual(count_2, count + 1)

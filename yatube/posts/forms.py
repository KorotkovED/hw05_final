from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta():
        model = Post
        fields = ('text', 'group', 'image')
        help_texts = {
            'text': 'Текст нового поста',
        }

    def not_empty_text(self):
        data = self.cleaned_data['text']
        if data == '':
            raise forms.ValidationError(
                'Кажется, все-таки нужно что-нибудь написать.')
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        help_text = {
            'text': 'Текст нового комментария'
        }

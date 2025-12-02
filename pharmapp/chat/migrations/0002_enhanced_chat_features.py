# Generated migration for enhanced chat features

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0002_chatmessage_edited_at_chatmessage_file_attachment_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='is_pinned',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='is_forwarded',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='forwarded_from',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='forwards', to='chat.chatmessage'),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='voice_duration',
            field=models.IntegerField(blank=True, help_text='Duration in seconds for voice messages', null=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='location_lat',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='location_lng',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=11, null=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='location_address',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='message_type',
            field=models.CharField(choices=[('text', 'Text'), ('file', 'File'), ('image', 'Image'), ('voice', 'Voice Message'), ('video', 'Video'), ('location', 'Location'), ('system', 'System Message')], default='text', max_length=10),
        ),
        migrations.CreateModel(
            name='MessageReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reaction', models.CharField(choices=[('👍', 'Like'), ('❤️', 'Love'), ('😂', 'Laugh'), ('😮', 'Wow'), ('😢', 'Sad'), ('😡', 'Angry'), ('👏', 'Clap'), ('🔥', 'Fire')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='chat.chatmessage')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatTheme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('primary_color', models.CharField(default='#007bff', max_length=7)),
                ('secondary_color', models.CharField(default='#6c757d', max_length=7)),
                ('background_color', models.CharField(default='#ffffff', max_length=7)),
                ('text_color', models.CharField(default='#000000', max_length=7)),
                ('bubble_color_sent', models.CharField(default='#007bff', max_length=7)),
                ('bubble_color_received', models.CharField(default='#e9ecef', max_length=7)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserChatPreferences',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_sound', models.BooleanField(default=True)),
                ('show_online_status', models.BooleanField(default=True)),
                ('auto_download_media', models.BooleanField(default=True)),
                ('font_size', models.CharField(choices=[('small', 'Small'), ('medium', 'Medium'), ('large', 'Large')], default='medium', max_length=10)),
                ('enter_to_send', models.BooleanField(default=True)),
                ('show_typing_indicator', models.BooleanField(default=True)),
                ('theme', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='chat.chattheme')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='chat_preferences', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='messagereaction',
            constraint=models.UniqueConstraint(fields=('message', 'user', 'reaction'), name='unique_message_user_reaction'),
        ),
    ]

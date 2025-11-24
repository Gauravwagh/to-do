from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notes.models import Notebook, Note
from django.utils.text import slugify

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up initial data for the application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of the user to create initial data for',
        )

    def handle(self, *args, **options):
        user_email = options.get('user_email')
        
        if not user_email:
            self.stdout.write(
                self.style.ERROR('Please provide --user-email argument')
            )
            return
        
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User with email {user_email} does not exist')
            )
            return
        
        # Create default notebook if it doesn't exist
        default_notebook, created = Notebook.objects.get_or_create(
            user=user,
            is_default=True,
            defaults={
                'name': 'Default',
                'description': 'Default notebook for your notes',
                'color': '#007bff'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created default notebook for {user.email}')
            )
        
        # Create some sample notebooks
        sample_notebooks = [
            {
                'name': 'Work',
                'description': 'Work-related notes and ideas',
                'color': '#28a745'
            },
            {
                'name': 'Personal',
                'description': 'Personal thoughts and reminders',
                'color': '#ffc107'
            },
            {
                'name': 'Ideas',
                'description': 'Creative ideas and inspiration',
                'color': '#e83e8c'
            }
        ]
        
        for notebook_data in sample_notebooks:
            notebook, created = Notebook.objects.get_or_create(
                user=user,
                name=notebook_data['name'],
                defaults={
                    'description': notebook_data['description'],
                    'color': notebook_data['color']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created notebook: {notebook.name}')
                )
        
        # Create sample notes
        sample_notes = [
            {
                'title': 'Welcome to Evernote Clone!',
                'content': '''
                <h2>Welcome to your new note-taking app!</h2>
                <p>This is a sample note to get you started. Here are some features you can explore:</p>
                <ul>
                    <li><strong>Rich Text Editing</strong> - Format your notes with bold, italic, lists, and more</li>
                    <li><strong>Notebooks</strong> - Organize your notes into different notebooks</li>
                    <li><strong>Tags</strong> - Add tags to categorize your notes</li>
                    <li><strong>Search</strong> - Find your notes quickly with full-text search</li>
                    <li><strong>Pin Notes</strong> - Pin important notes to keep them at the top</li>
                </ul>
                <p>Start creating your own notes and make this app your own!</p>
                ''',
                'notebook': default_notebook,
                'tags': ['welcome', 'getting-started'],
                'is_pinned': True
            },
            {
                'title': 'Meeting Notes Template',
                'content': '''
                <h2>Meeting Notes - [Date]</h2>
                <p><strong>Attendees:</strong></p>
                <ul>
                    <li>Person 1</li>
                    <li>Person 2</li>
                </ul>
                
                <p><strong>Agenda:</strong></p>
                <ol>
                    <li>Topic 1</li>
                    <li>Topic 2</li>
                    <li>Topic 3</li>
                </ol>
                
                <p><strong>Action Items:</strong></p>
                <ul>
                    <li>[ ] Task 1 - Assigned to: Person</li>
                    <li>[ ] Task 2 - Assigned to: Person</li>
                </ul>
                
                <p><strong>Next Steps:</strong></p>
                <p>Follow up on action items by [date]</p>
                ''',
                'notebook': Notebook.objects.filter(user=user, name='Work').first() or default_notebook,
                'tags': ['meeting', 'template', 'work']
            },
            {
                'title': 'Project Ideas',
                'content': '''
                <h2>Project Ideas</h2>
                <p>A collection of project ideas to work on:</p>
                
                <h3>Web Development</h3>
                <ul>
                    <li>Personal portfolio website</li>
                    <li>Recipe sharing platform</li>
                    <li>Task management app</li>
                </ul>
                
                <h3>Mobile Apps</h3>
                <ul>
                    <li>Habit tracker</li>
                    <li>Local event finder</li>
                    <li>Expense tracker</li>
                </ul>
                
                <h3>Data Science</h3>
                <ul>
                    <li>Weather prediction model</li>
                    <li>Stock price analysis</li>
                    <li>Social media sentiment analysis</li>
                </ul>
                ''',
                'notebook': Notebook.objects.filter(user=user, name='Ideas').first() or default_notebook,
                'tags': ['projects', 'ideas', 'development']
            }
        ]
        
        for note_data in sample_notes:
            note, created = Note.objects.get_or_create(
                user=user,
                title=note_data['title'],
                defaults={
                    'content': note_data['content'],
                    'notebook': note_data['notebook'],
                    'is_pinned': note_data.get('is_pinned', False)
                }
            )
            
            if created:
                # Add tags
                for tag_name in note_data.get('tags', []):
                    note.tags.add(tag_name)
                
                self.stdout.write(
                    self.style.SUCCESS(f'Created note: {note.title}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up initial data for {user.email}'
            )
        )










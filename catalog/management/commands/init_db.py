"""
Management command to initialize the database with sample data
"""
from django.core.management.base import BaseCommand
from catalog.models import BoardGame
from decimal import Decimal


class Command(BaseCommand):
    help = 'Initialize database with sample board games'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample board games...')
        
        # Check if games already exist
        if BoardGame.objects.exists():
            self.stdout.write(self.style.WARNING('Database already has games. Skipping.'))
            return
        
        sample_games = [
            {
                'name': 'Catan',
                'description': 'Settlers of Catan is a multiplayer board game designed by Klaus Teuber.',
                'year_published': 1995,
                'designer': 'Klaus Teuber',
                'min_players': 3,
                'max_players': 4,
                'min_playtime': 60,
                'max_playtime': 120,
                'min_age': 10,
                'condition': 'used',
                'msrp_price': Decimal('49.99'),
                'stock_quantity': 2,
            },
            {
                'name': 'Ticket to Ride',
                'description': 'Ticket to Ride is a railway-themed German-style board game.',
                'year_published': 2004,
                'designer': 'Alan R. Moon',
                'min_players': 2,
                'max_players': 5,
                'min_playtime': 30,
                'max_playtime': 60,
                'min_age': 8,
                'condition': 'like_new',
                'msrp_price': Decimal('44.99'),
                'stock_quantity': 1,
            },
            {
                'name': 'Pandemic',
                'description': 'Pandemic is a cooperative board game where players work as a team to treat infections.',
                'year_published': 2008,
                'designer': 'Matt Leacock',
                'min_players': 2,
                'max_players': 4,
                'min_playtime': 45,
                'max_playtime': 60,
                'min_age': 8,
                'condition': 'new',
                'msrp_price': Decimal('39.99'),
                'stock_quantity': 3,
            },
        ]
        
        for game_data in sample_games:
            game = BoardGame.objects.create(**game_data)
            self.stdout.write(self.style.SUCCESS(f'Created: {game.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(sample_games)} sample games!'))

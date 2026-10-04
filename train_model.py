import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Update database first
try:
    from migrate_db import migrate_database
    print("Updating database...")
    migrate_database()
except Exception as e:
    print(f"Warning: Error updating database: {e}")

from app import app, db, Ticket, TicketCategory
from ai_model import AITicketModel
import json

def prepare_training_data():
    with app.app_context():
        tickets = Ticket.query.all()
        training_data = []
        
        for ticket in tickets:
            # Get category from TicketCategory
            category_obj = TicketCategory.query.filter_by(ticket_id=ticket.id).first()
            category = category_obj.category if category_obj else 'other'
            
            # Handle new columns safely
            ticket_type = getattr(ticket, 'ticket_type', None) or 'printer'
            
            training_data.append({
                'title': ticket.title or '',
                'description': ticket.description or '',
                'category': category,
                'priority': ticket.priority or 'Low',
                'ticket_type': ticket_type
            })
        
        print(f"Prepared {len(training_data)} tickets for training")
        return training_data

def train_ai_model(epochs=50):
    print("=" * 50)
    print("Starting AI model training")
    print("=" * 50)
    
    # Prepare data
    training_data = prepare_training_data()
    
    if len(training_data) < 10:
        print("Warning: Too few tickets for good training")
        print("Recommended: at least 50+ tickets for effective training")
        response = input("Do you want to continue? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Create and train model
    model = AITicketModel(
        vocab_size=5000,
        max_length=200,
        embedding_dim=128
    )
    
    try:
        history = model.train(
            training_data,
            epochs=epochs,
            batch_size=32,
            validation_split=0.2
        )
        
        # Save model
        model.save_model('models')
        
        print("\n" + "=" * 50)
        print("Training completed successfully!")
        print("=" * 50)
        print(f"\nTraining Statistics:")
        print(f"- Number of samples: {len(training_data)}")
        print(f"- Category accuracy: {history.history.get('category_accuracy', [0])[-1]:.2%}")
        print(f"- Priority accuracy: {history.history.get('priority_accuracy', [0])[-1]:.2%}")
        print(f"\nModel saved in 'models' folder")
        
    except Exception as e:
        print(f"\nError during training: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Train AI model')
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    args = parser.parse_args()
    
    train_ai_model(epochs=args.epochs)


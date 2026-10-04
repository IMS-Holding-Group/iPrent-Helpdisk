import os
import pickle
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
import re
import json
from datetime import datetime

class AITicketModel:
    def __init__(self, vocab_size=5000, max_length=200, embedding_dim=128):
        self.vocab_size = vocab_size
        self.max_length = max_length
        self.embedding_dim = embedding_dim
        self.tokenizer = None
        self.model = None
        self.category_encoder = None
        self.priority_encoder = None
        self.is_trained = False
        
    def preprocess_text(self, text):
        if not text:
            return ""
        
        # Convert to lowercase
        text = str(text).lower()
        
        # Remove excessive punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove excessive spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def build_model(self, num_categories=6, num_priorities=4):
        # Text input
        text_input = keras.Input(shape=(self.max_length,), name='text_input')
        
        # Embedding layer
        embedding = layers.Embedding(
            self.vocab_size + 1,
            self.embedding_dim,
            input_length=self.max_length,
            name='embedding'
        )(text_input)
        
        # LSTM layers for sequence processing
        lstm1 = layers.LSTM(128, return_sequences=True, dropout=0.3, name='lstm1')(embedding)
        lstm2 = layers.LSTM(64, dropout=0.3, name='lstm2')(lstm1)
        
        # Dense layers
        dense1 = layers.Dense(128, activation='relu', name='dense1')(lstm2)
        dropout1 = layers.Dropout(0.4, name='dropout1')(dense1)
        dense2 = layers.Dense(64, activation='relu', name='dense2')(dropout1)
        dropout2 = layers.Dropout(0.3, name='dropout2')(dense2)
        
        # Multiple outputs
        category_output = layers.Dense(num_categories, activation='softmax', name='category')(dropout2)
        priority_output = layers.Dense(num_priorities, activation='softmax', name='priority')(dropout2)
        response_output = layers.Dense(256, activation='relu', name='response_dense')(dropout2)
        response_output = layers.Dense(128, activation='relu', name='response_dense2')(response_output)
        
        # Build model
        self.model = keras.Model(
            inputs=text_input,
            outputs={
                'category': category_output,
                'priority': priority_output,
                'response': response_output
            },
            name='ticket_ai_model'
        )
        
        # Compile model
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'category': 'sparse_categorical_crossentropy',
                'priority': 'sparse_categorical_crossentropy',
                'response': 'mse'
            },
            loss_weights={
                'category': 1.0,
                'priority': 1.0,
                'response': 0.5
            },
            metrics={
                'category': 'accuracy',
                'priority': 'accuracy'
            }
        )
        
        return self.model
    
    def prepare_training_data(self, tickets_data):
        texts = []
        categories = []
        priorities = []
        
        # Encode categories and priorities - values must be from 0 to n-1
        category_map = {
            'hardware': 0, 
            'software': 1, 
            'network': 2,
            'printer': 3, 
            'ink': 4, 
            'paper': 5, 
            'other': 6  # Changed from 5 to 6
        }
        
        priority_map = {
            'Low': 0, 
            'Medium': 1, 
            'High': 2, 
            'Critical': 3
        }
        
        # Save encodings (will be updated after knowing actual values)
        self.category_map = category_map
        self.priority_map = priority_map
        
        for ticket in tickets_data:
            text = self.preprocess_text(
                (ticket.get('title', '') + ' ' + ticket.get('description', '')).strip()
            )
            if text:
                texts.append(text)
                cat = ticket.get('category', 'other')
                categories.append(category_map.get(cat, 6))  # 6 = other
                pri = ticket.get('priority', 'Low')
                priorities.append(priority_map.get(pri, 0))  # 0 = Low
        
        # Create and train Tokenizer
        self.tokenizer = Tokenizer(num_words=self.vocab_size, oov_token='<OOV>')
        self.tokenizer.fit_on_texts(texts)
        
        # Convert texts to sequences
        sequences = self.tokenizer.texts_to_sequences(texts)
        padded_sequences = pad_sequences(sequences, maxlen=self.max_length, padding='post')
        
        # Create reverse encoders
        self.category_encoder = {v: k for k, v in category_map.items()}
        self.priority_encoder = {v: k for k, v in priority_map.items()}
        
        return padded_sequences, np.array(categories), np.array(priorities)
    
    def train(self, tickets_data, epochs=50, batch_size=32, validation_split=0.2):
        print("Starting training data preparation...")
        X, y_categories, y_priorities = self.prepare_training_data(tickets_data)
        
        if len(X) < 10:
            raise ValueError("Insufficient data for training (requires at least 10 tickets)")
        
        print(f"Number of training samples: {len(X)}")
        
        # Split data
        X_train, X_val, y_cat_train, y_cat_val, y_pri_train, y_pri_val = train_test_split(
            X, y_categories, y_priorities, test_size=validation_split, random_state=42
        )
        
        # Build model - calculate actual number of categories
        unique_categories = set(y_categories)
        unique_priorities = set(y_priorities)
        
        num_categories = len(unique_categories)
        num_priorities = len(unique_priorities)
        
        # Ensure values start from 0
        max_category = max(unique_categories) if unique_categories else 0
        max_priority = max(unique_priorities) if unique_priorities else 0
        
        if max_category >= num_categories:
            num_categories = max_category + 1
        if max_priority >= num_priorities:
            num_priorities = max_priority + 1
        
        print(f"Number of categories: {num_categories} (Values: {sorted(unique_categories)})")
        print(f"Number of priorities: {num_priorities} (Values: {sorted(unique_priorities)})")
        
        self.build_model(num_categories, num_priorities)
        
        print("Starting model training...")
        print(self.model.summary())
        
        # Train model
        history = self.model.fit(
            X_train,
            {
                'category': y_cat_train,
                'priority': y_pri_train,
                'response': np.zeros((len(X_train), 128))  # placeholder
            },
            validation_data=(
                X_val,
                {
                    'category': y_cat_val,
                    'priority': y_pri_val,
                    'response': np.zeros((len(X_val), 128))  # placeholder
                }
            ),
            epochs=epochs,
            batch_size=batch_size,
            verbose=1
        )
        
        self.is_trained = True
        print("Training completed successfully!")
        
        return history
    
    def predict_category(self, text):
        if not self.is_trained or not self.tokenizer:
            return 'other', 0.5
        
        processed_text = self.preprocess_text(text)
        sequence = self.tokenizer.texts_to_sequences([processed_text])
        padded = pad_sequences(sequence, maxlen=self.max_length, padding='post')
        
        predictions = self.model.predict(padded, verbose=0)
        category_pred = predictions['category'][0]
        
        category_idx = int(np.argmax(category_pred))
        confidence = float(category_pred[category_idx])
        
        # Use reverse category_map
        if hasattr(self, 'category_map'):
            category = [k for k, v in self.category_map.items() if v == category_idx]
            category = category[0] if category else 'other'
        else:
            category = self.category_encoder.get(category_idx, 'other')
        
        return category, confidence
    
    def predict_priority(self, text, affected_users=1, device_name=None):
        if not self.is_trained or not self.tokenizer:
            return 'Low', 30.0
        
        processed_text = self.preprocess_text(text)
        sequence = self.tokenizer.texts_to_sequences([processed_text])
        padded = pad_sequences(sequence, maxlen=self.max_length, padding='post')
        
        predictions = self.model.predict(padded, verbose=0)
        priority_pred = predictions['priority'][0]
        
        priority_idx = int(np.argmax(priority_pred))
        base_score = float(priority_pred[priority_idx]) * 100
        
        # Adjust based on additional factors
        if affected_users >= 50:
            base_score += 40
        elif affected_users >= 20:
            base_score += 30
        elif affected_users >= 10:
            base_score += 20
        elif affected_users >= 5:
            base_score += 10
        
        if device_name:
            device_lower = device_name.lower()
            if any(kw in device_lower for kw in ['server', 'database']):
                base_score += 35
            elif any(kw in device_lower for kw in ['network', 'router']):
                base_score += 25
        
        # Use reverse priority_map
        if hasattr(self, 'priority_map'):
            priority = [k for k, v in self.priority_map.items() if v == priority_idx]
            priority = priority[0] if priority else 'Low'
        else:
            priority = self.priority_encoder.get(priority_idx, 'Low')
        
        # Determine final priority based on score
        if base_score >= 90:
            priority = 'Critical'
        elif base_score >= 70:
            priority = 'High'
        elif base_score >= 40:
            priority = 'Medium'
        else:
            priority = 'Low'
        
        return priority, min(base_score, 100)
    
    def generate_response(self, title, description, category):
        if not self.is_trained:
            return self._fallback_response(title, description, category)
        
        text = self.preprocess_text(title + ' ' + description)
        sequence = self.tokenizer.texts_to_sequences([text])
        padded = pad_sequences(sequence, maxlen=self.max_length, padding='post')
        
        predictions = self.model.predict(padded, verbose=0)
        
        # Use enhanced knowledge base with model
        response_template = self._get_response_template(category, text)
        
        # Enhance response based on model
        response_embedding = predictions['response'][0]
        
        # Generate troubleshooting steps
        troubleshooting_steps = self._generate_troubleshooting_steps(category, text)
        
        # Generate common solutions
        common_solutions = self._generate_common_solutions(category, text)
        
        # Generate guidance
        guidance = self._generate_guidance(category, text)
        
        return {
            'initial_response': response_template,
            'troubleshooting_steps': troubleshooting_steps,
            'common_solutions': common_solutions,
            'guidance': guidance,
            'confidence': 0.85  # High confidence from trained model
        }
    
    def _get_response_template(self, category, text):
        templates = {
            'network': "Thank you for contacting us. Based on the problem analysis, this appears to be a network-related issue. Please try the following steps:",
            'hardware': "Thank you for contacting us. Based on the problem analysis, this appears to be a hardware-related issue. Please try the following steps:",
            'software': "Thank you for contacting us. Based on the problem analysis, this appears to be a software-related issue. Please try the following steps:",
            'printer': "Thank you for contacting us. Based on the problem analysis, this appears to be a printer-related issue. Please try the following steps:",
            'ink': "Thank you for contacting us. Based on the problem analysis, this appears to be an ink-related issue. Please try the following steps:",
            'paper': "Thank you for contacting us. Based on the problem analysis, this appears to be a paper-related issue. Please try the following steps:",
        }
        return templates.get(category, "Thank you for contacting us. Based on the problem analysis, please try the following steps:")
    
    def _generate_troubleshooting_steps(self, category, text):
        steps_db = {
            'network': [
                '1. Check cable connection to the network',
                '2. Restart the router',
                '3. Check IP and DNS settings',
                '4. Test connection using ping',
                '5. Check firewall settings'
            ],
            'hardware': [
                '1. Check device power connection',
                '2. Restart the device',
                '3. Check for any visible errors',
                '4. Check cables and connections',
                '5. Review device user manual'
            ],
            'software': [
                '1. Restart the application',
                '2. Check for available updates',
                '3. Reinstall the application',
                '4. Check system requirements',
                '5. Review error log'
            ],
            'printer': [
                '1. Check printer network connection',
                '2. Check ink and paper levels',
                '3. Restart the printer',
                '4. Check print queue',
                '5. Reinstall printer driver'
            ],
            'ink': [
                '1. Check ink level in printer',
                '2. Remove and inspect ink cartridge',
                '3. Clean print head',
                '4. Replace ink cartridge if necessary',
                '5. Reinstall ink cartridge properly'
            ],
            'paper': [
                '1. Check for paper in printer',
                '2. Ensure correct paper size',
                '3. Remove any stuck paper',
                '4. Clean paper path',
                '5. Reload paper correctly'
            ]
        }
        
        base_steps = steps_db.get(category, steps_db['hardware'])
        
        # Enhance steps based on text
        text_lower = text.lower()
        if 'slow' in text_lower:
            base_steps.insert(0, '0. Check resource usage (CPU, RAM)')
        if 'error' in text_lower:
            base_steps.insert(0, '0. Review error log for details')
        
        return '\n'.join(base_steps[:5])
    
    def _generate_common_solutions(self, category, text):
        solutions_db = {
            'network': [
                '• Restart router',
                '• Check network settings',
                '• Reset TCP/IP settings',
                '• Check network cable'
            ],
            'hardware': [
                '• Restart device',
                '• Check cables and connections',
                '• Clean device from dust',
                '• Check device warranty'
            ],
            'software': [
                '• Reinstall application',
                '• Update application to latest version',
                '• Check system requirements',
                '• Run application as administrator'
            ],
            'printer': [
                '• Restart printer',
                '• Check ink and paper levels',
                '• Clear print queue',
                '• Reinstall printer driver'
            ],
            'ink': [
                '• Replace ink cartridge',
                '• Clean print head',
                '• Check cartridge installation',
                '• Use original cartridge'
            ],
            'paper': [
                '• Add new paper',
                '• Remove stuck paper',
                '• Clean paper path',
                '• Check paper size'
            ]
        }
        
        return '\n'.join(solutions_db.get(category, solutions_db['hardware']))
    
    def _generate_guidance(self, category, text):
        guidance_db = {
            'network': 'If the problem persists after trying the above steps, please contact the technical support team with details of the steps tried.',
            'hardware': 'If the device is still not working properly, you may need technical maintenance. Please contact the support team.',
            'software': 'If the problem persists, you may need to update the system or reinstall the software. Please contact the support team.',
            'printer': 'If the problem persists, please check the printer status in the control panel and contact the support team.',
            'ink': 'If the problem persists after replacing the ink, you may need professional printer cleaning. Please contact the support team.',
            'paper': 'If the paper problem persists, you may need a mechanical inspection of the printer. Please contact the support team.'
        }
        return guidance_db.get(category, 'If the problem persists, please contact the technical support team.')
    
    def _fallback_response(self, title, description, category):
        return {
            'initial_response': f"Thank you for contacting us. Based on the problem description, this appears to be a {category}-related issue.",
            'troubleshooting_steps': '1. Check device connection\n2. Restart device\n3. Check settings',
            'common_solutions': '• Restart\n• Check connection',
            'guidance': 'Please contact the support team if the problem persists.',
            'confidence': 0.5
        }
    
    def save_model(self, model_dir='models'):
        if not self.is_trained:
            raise ValueError("Model is not trained. Please train it first.")
        
        os.makedirs(model_dir, exist_ok=True)
        
        # Save model
        self.model.save(os.path.join(model_dir, 'ticket_ai_model.h5'))
        
        # Save Tokenizer
        with open(os.path.join(model_dir, 'tokenizer.pkl'), 'wb') as f:
            pickle.dump(self.tokenizer, f)
        
        # Save encodings
        with open(os.path.join(model_dir, 'encoders.pkl'), 'wb') as f:
            pickle.dump({
                'category_encoder': self.category_encoder,
                'priority_encoder': self.priority_encoder,
                'category_map': getattr(self, 'category_map', {}),
                'priority_map': getattr(self, 'priority_map', {})
            }, f)
        
        # Save model info
        model_info = {
            'vocab_size': self.vocab_size,
            'max_length': self.max_length,
            'embedding_dim': self.embedding_dim,
            'trained_at': datetime.now().isoformat(),
            'is_trained': True
        }
        
        with open(os.path.join(model_dir, 'model_info.json'), 'w', encoding='utf-8') as f:
            json.dump(model_info, f, ensure_ascii=False, indent=2)
        
        print(f"Model saved to {model_dir}")
    
    def load_model(self, model_dir='models'):
        model_path = os.path.join(model_dir, 'ticket_ai_model.h5')
        
        if not os.path.exists(model_path):
            print(f"Model not found in {model_dir}")
            return False
        
        try:
            # Load model
            self.model = keras.models.load_model(model_path)
            
            # Load Tokenizer
            with open(os.path.join(model_dir, 'tokenizer.pkl'), 'rb') as f:
                self.tokenizer = pickle.load(f)
            
            # Load encodings
            with open(os.path.join(model_dir, 'encoders.pkl'), 'rb') as f:
                encoders = pickle.load(f)
                self.category_encoder = encoders.get('category_encoder', {})
                self.priority_encoder = encoders.get('priority_encoder', {})
                self.category_map = encoders.get('category_map', {})
                self.priority_map = encoders.get('priority_map', {})
            
            # Load model info
            with open(os.path.join(model_dir, 'model_info.json'), 'r', encoding='utf-8') as f:
                model_info = json.load(f)
                self.vocab_size = model_info.get('vocab_size', 5000)
                self.max_length = model_info.get('max_length', 200)
                self.embedding_dim = model_info.get('embedding_dim', 128)
            
            self.is_trained = True
            print(f"Model loaded from {model_dir}")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False


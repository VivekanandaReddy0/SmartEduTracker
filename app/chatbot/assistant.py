import logging
import random
from flask import current_app
from app.models import ChatHistory, db
from flask_login import current_user

# Education-focused responses
EDUCATIONAL_RESPONSES = {
    "study_tips": [
        "Create a dedicated study space free from distractions to improve focus.",
        "Use active recall techniques - test yourself instead of just re-reading notes.",
        "The Pomodoro Technique (25 min study, 5 min break) can improve productivity.",
        "Break large topics into smaller, manageable chunks for better understanding.",
        "Teaching concepts to others is one of the best ways to solidify your understanding.",
        "Space out your study sessions over time rather than cramming before exams.",
    ],
    "motivation": [
        "Remember your 'why' - connect your current studies to your long-term goals.",
        "Progress takes time. Even small improvements compound over time.",
        "Mistakes and failures are valuable learning opportunities, not setbacks.",
        "Focus on the process of learning rather than just grades or outcomes.",
        "Celebrate small wins along your educational journey to maintain motivation.",
    ],
    "exam_preparation": [
        "Create a study schedule with specific topics for each day leading up to the exam.",
        "Practice with past papers to familiarize yourself with the exam format.",
        "Form study groups to discuss difficult concepts and test each other.",
        "Prioritize topics based on their importance and your current understanding.",
        "Take care of your physical health - proper sleep, nutrition and exercise improve cognition.",
    ],
    "research_skills": [
        "Start with broad searches, then narrow down using specific keywords.",
        "Evaluate sources for credibility, authority, accuracy, and currency.",
        "Take organized notes with proper citations to avoid unintentional plagiarism.",
        "Synthesize information from multiple sources rather than relying on just one.",
        "Don't hesitate to reach out to professors or librarians for research guidance.",
    ],
    "time_management": [
        "Use a planner or digital calendar to track all assignments and deadlines.",
        "Prioritize tasks using the Eisenhower Matrix (urgent/important categorization).",
        "Learn to say no to commitments that don't align with your current priorities.",
        "Identify your most productive hours and schedule challenging tasks during those times.",
        "Break large projects into smaller milestones with their own deadlines.",
    ],
    "general": [
        "What specific subject are you currently finding most challenging?",
        "Learning styles vary - visual, auditory, reading/writing, and kinesthetic. Which works best for you?",
        "Building strong fundamentals is essential before moving to advanced concepts.",
        "Regular review sessions help transfer knowledge from short-term to long-term memory.",
        "The journey of education is as valuable as the destination. Enjoy the process of learning!",
    ]
}

# Subject-specific responses
SUBJECT_RESPONSES = {
    "math": [
        "Mathematics is best learned through consistent practice and problem-solving.",
        "When studying math, focus on understanding concepts rather than memorizing formulas.",
        "For complex math problems, try breaking them down into smaller, more manageable steps.",
        "Creating visual representations can help understand abstract mathematical concepts.",
    ],
    "science": [
        "The scientific method is a powerful framework for inquiry: observe, question, hypothesize, test, analyze, conclude.",
        "Connect scientific concepts to real-world applications to deepen understanding.",
        "Drawing diagrams can help visualize scientific processes and relationships.",
        "Science evolves through evidence-based refinement - be open to updating your understanding.",
    ],
    "programming": [
        "Learning to program is like learning a language - regular practice is key.",
        "Don't just read code - write it, experiment with it, and debug it to truly learn.",
        "Start with small, achievable projects that interest you to maintain motivation.",
        "The ability to decompose problems into smaller parts is essential for programming.",
    ],
    "literature": [
        "Annotate texts as you read to engage actively with the material.",
        "Consider historical and cultural contexts to deepen your understanding of literature.",
        "Look for patterns, symbols, and themes that connect different parts of a text.",
        "Practice analytical writing to develop your ability to form and support interpretations.",
    ],
    "history": [
        "History is not just memorizing dates, but understanding causes, effects, and patterns.",
        "Primary sources offer direct windows into historical periods and perspectives.",
        "Consider multiple perspectives when studying historical events and figures.",
        "Creating timelines can help visualize the relationship between different historical events.",
    ],
    "languages": [
        "Immerse yourself in the language through media, music, and conversation practice.",
        "Consistent daily practice is more effective than occasional intensive study.",
        "Focus on practical vocabulary and phrases you'll actually use in conversation.",
        "Don't fear making mistakes - they're an essential part of the language learning process.",
    ]
}

def get_ai_response(message, history=[]):
    """
    Generate a contextual educational response based on the user's message
    
    Args:
        message (str): User message
        history (list): List of previous messages in the conversation
    
    Returns:
        str: AI response
    """
    try:
        message_lower = message.lower()
        response = ""
        
        # Check if message contains keywords related to specific topics
        if any(word in message_lower for word in ["study", "learn", "memorize", "focus"]):
            response = random.choice(EDUCATIONAL_RESPONSES["study_tips"])
        
        elif any(word in message_lower for word in ["motivate", "motivation", "uninspired", "discouraged"]):
            response = random.choice(EDUCATIONAL_RESPONSES["motivation"])
        
        elif any(word in message_lower for word in ["exam", "test", "finals", "prepare"]):
            response = random.choice(EDUCATIONAL_RESPONSES["exam_preparation"])
        
        elif any(word in message_lower for word in ["research", "sources", "paper", "thesis"]):
            response = random.choice(EDUCATIONAL_RESPONSES["research_skills"])
        
        elif any(word in message_lower for word in ["time", "schedule", "organize", "planning"]):
            response = random.choice(EDUCATIONAL_RESPONSES["time_management"])
        
        # Check for subject-specific queries
        elif any(word in message_lower for word in ["math", "calculus", "algebra", "equation"]):
            response = random.choice(SUBJECT_RESPONSES["math"])
        
        elif any(word in message_lower for word in ["science", "biology", "chemistry", "physics"]):
            response = random.choice(SUBJECT_RESPONSES["science"])
        
        elif any(word in message_lower for word in ["programming", "code", "python", "java"]):
            response = random.choice(SUBJECT_RESPONSES["programming"])
        
        elif any(word in message_lower for word in ["literature", "book", "novel", "poem"]):
            response = random.choice(SUBJECT_RESPONSES["literature"])
        
        elif any(word in message_lower for word in ["history", "historical", "past", "century"]):
            response = random.choice(SUBJECT_RESPONSES["history"])
        
        elif any(word in message_lower for word in ["language", "spanish", "french", "english"]):
            response = random.choice(SUBJECT_RESPONSES["languages"])
        
        # If no specific topic is detected, provide a general educational response
        else:
            response = random.choice(EDUCATIONAL_RESPONSES["general"])
        
        # Common greetings
        if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            greeting = "Hello! I'm your educational assistant. "
            response = greeting + response
        
        # Common questions about the assistant
        if "who are you" in message_lower or "what can you do" in message_lower:
            return "I'm SmartEdu's educational assistant. I can provide study tips, answer questions about various subjects, help with exam preparation, and offer guidance on research skills and time management."
        
        # Thank you responses
        if "thank" in message_lower or "thanks" in message_lower:
            return "You're welcome! Is there anything else I can help you with regarding your studies?"
        
        # Store chat history if user is logged in
        if current_user and not current_user.is_anonymous:
            try:
                chat_entry = ChatHistory(
                    user_id=current_user.id,
                    message=message,
                    response=response
                )
                db.session.add(chat_entry)
                db.session.commit()
            except Exception as e:
                logging.error(f"Error saving chat history: {str(e)}")
                db.session.rollback()
        
        return response
        
    except Exception as e:
        logging.error(f"Error in get_ai_response: {str(e)}")
        return "I'm here to help with your educational questions. What subject or topic would you like assistance with?"

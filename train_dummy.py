import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
import os

texts = [
    "hello world", "how are you", "good morning", "what is your name",
    "bonjour le monde", "comment allez vous", "je m'appelle",
    "hola mundo", "como estas", "buenos dias",
    "hallo welt", "wie geht es dir", "guten morgen"
]
labels = ["en", "en", "en", "en", "fr", "fr", "fr", "es", "es", "es", "de", "de", "de"]

pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(analyzer='char', ngram_range=(2,4))),
    ('clf', LinearSVC())
])

pipeline.fit(texts, labels)
os.makedirs('model', exist_ok=True)
joblib.dump(pipeline, 'model/svm_model.pkl')
print("Dummy Model trained and saved.")

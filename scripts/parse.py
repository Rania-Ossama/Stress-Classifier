# import zstandard as zstd
# import json
# import pandas as pd
# import os
# from tqdm import tqdm

# # Define your subreddits and their stress labels
# SUBREDDIT_LABELS = {
#     # High Stress
#     'stress': 'high',
#     'Anxiety': 'high',
#     'socialanxiety': 'high',
#     'depression': 'high',
#     'PTSD': 'high',
#     'offmychest': 'high',
#     'TrueOffMyChest': 'high',
    
#     # Medium Stress
#     'work': 'medium',
#     'remotework': 'medium',
#     'relationship_advice': 'medium',
    
#     # Low Stress
#     'happy': 'low',
#     'singleandhappy': 'low',
#     'CasualConversation': 'low',
# }

# def read_zst_file(filepath):
#     """Read and decompress a .zst file line by line"""
#     with open(filepath, 'rb') as f:
#         dctx = zstd.ZstdDecompressor()
#         with dctx.stream_reader(f) as reader:
#             buffer = b""
#             while True:
#                 chunk = reader.read(65536)
#                 if not chunk:
#                     break
#                 buffer += chunk
#                 lines = buffer.split(b'\n')
#                 buffer = lines[-1]
#                 for line in lines[:-1]:
#                     if line.strip():
#                         try:
#                             yield json.loads(line)
#                         except json.JSONDecodeError:
#                             continue

# def parse_all_files(raw_folder, output_folder, max_per_subreddit=15000):
#     """Parse all .zst files and save to CSV"""
#     os.makedirs(output_folder, exist_ok=True)
#     all_data = []
    
#     for filename in os.listdir(raw_folder):
#         if not filename.endswith('.zst'):
#             continue
            
#         # Get subreddit name from filename
#         subreddit = filename.replace('_submissions.zst', '')
        
#         if subreddit not in SUBREDDIT_LABELS:
#             print(f"Skipping {filename} - not in target list")
#             continue
            
#         label = SUBREDDIT_LABELS[subreddit]
#         filepath = os.path.join(raw_folder, filename)
        
#         print(f"\nProcessing {filename} → Label: {label}")
        
#         count = 0
#         for post in tqdm(read_zst_file(filepath)):
#             if count >= max_per_subreddit:
#                 break
                
#             # Extract only what we need
#             title = post.get('title', '')
#             body = post.get('selftext', '')
            
#             # Skip deleted/removed posts
#             if body in ['[deleted]', '[removed]', '']:
#                 continue
                
#             # Skip very short posts
#             full_text = f"{title} {body}".strip()
#             if len(full_text.split()) < 20:
#                 continue
            
#             all_data.append({
#                 'title': title,
#                 'text': body,
#                 'full_text': full_text,
#                 'subreddit': subreddit,
#                 'stress_label': label
#             })
#             count += 1
        
#         print(f"✅ Collected {count} posts from r/{subreddit}")
    
#     # Save to CSV
#     df = pd.DataFrame(all_data)
#     output_path = os.path.join(output_folder, 'parsed_data.csv')
#     df.to_csv(output_path, index=False)
#     print(f"\n🎉 Total posts collected: {len(df)}")
#     print(f"📊 Label distribution:\n{df['stress_label'].value_counts()}")
#     print(f"💾 Saved to {output_path}")
    
#     return df

# # Run it
# if __name__ == "__main__":
#     raw_folder = r"F:\UNIVERSITY\NU 3\semester 2\Machine Intelligence\Project\StressClassifier\data\raw"
#     output_folder = r"F:\UNIVERSITY\NU 3\semester 2\Machine Intelligence\Project\StressClassifier\data\parsed"
#     df = parse_all_files(raw_folder, output_folder, max_per_subreddit=15000)



import zstandard as zstd
import json
import pandas as pd
import os
import re
from tqdm import tqdm

# Define your subreddits and their stress labels
SUBREDDIT_LABELS = {
    'stress': 'high',
    'Anxiety': 'high',
    'socialanxiety': 'high',
    'depression': 'high',
    'PTSD': 'high',
    'offmychest': 'high',
    'TrueOffMyChest': 'high',
    'work': 'medium',
    'remotework': 'medium',
    'relationship_advice': 'medium',
    'happy': 'low',
    'singleandhappy': 'low',
    'CasualConversation': 'low',
}

# ❌ Keywords that indicate spam/irrelevant posts
SPAM_KEYWORDS = [
    'hiring', 'job posting', 'apply now', 'we are recruiting',
    'click here', 'check out my', 'follow me', 'subscribe',
    'discount', 'promo code', 'buy now', 'free trial',
    'http', 'www.', '.com', '.net', 'sign up',
    'referral', 'affiliate', 'sponsored'
]

# ✅ Keywords that confirm stress-related content
STRESS_INDICATORS = {
    'high': [
        'stress', 'anxiety', 'panic', 'overwhelm', 'depress',
        'trauma', 'ptsd', 'breakdown', 'crisis', 'hopeless',
        'exhausted', 'cant cope', "can't cope", 'suffering',
        'mental health', 'therapy', 'medication', 'crying',
        'scared', 'terrified', 'helpless', 'worthless'
    ],
    'medium': [
        'tired', 'worried', 'frustrated', 'difficult', 'struggle',
        'problem', 'issue', 'conflict', 'argument', 'pressure',
        'deadline', 'boss', 'relationship', 'fight', 'upset',
        'annoyed', 'concerned', 'nervous', 'uneasy'
    ],
    'low': [
        'happy', 'good', 'great', 'wonderful', 'blessed',
        'grateful', 'excited', 'love', 'enjoy', 'fun',
        'peaceful', 'calm', 'relaxed', 'content', 'positive',
        'amazing', 'awesome', 'thankful', 'smile', 'laugh'
    ]
}

def is_spam(text):
    """Check if post contains spam/irrelevant content"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SPAM_KEYWORDS)

def has_stress_indicator(text, label):
    """Check if post contains at least one relevant keyword"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in STRESS_INDICATORS[label])

def is_quality_post(text, min_words=30, max_words=500):
    """Check if post meets quality standards"""
    words = text.split()
    return min_words <= len(words) <= max_words

def clean_text(text):
    """Basic text cleaning"""
    # Remove URLs
    text = re.sub(r'http\S+|www\S+', '', text)
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\'\"-]', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def read_zst_file(filepath):
    """Read and decompress a .zst file line by line"""
    with open(filepath, 'rb') as f:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(f) as reader:
            buffer = b""
            while True:
                chunk = reader.read(65536)
                if not chunk:
                    break
                buffer += chunk
                lines = buffer.split(b'\n')
                buffer = lines[-1]
                for line in lines[:-1]:
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue

def parse_all_files(raw_folder, output_folder, max_per_subreddit=15000):
    """Parse all .zst files and save to CSV"""
    os.makedirs(output_folder, exist_ok=True)
    all_data = []

    # Track filtering stats for your paper
    stats = {
        'total_seen': 0,
        'deleted_removed': 0,
        'too_short': 0,
        'too_long': 0,
        'spam_filtered': 0,
        'no_stress_indicator': 0,
        'kept': 0
    }

    for filename in os.listdir(raw_folder):
        if not filename.endswith('.zst'):
            continue

        subreddit = filename.replace('_submissions.zst', '')

        if subreddit not in SUBREDDIT_LABELS:
            print(f"Skipping {filename} - not in target list")
            continue

        label = SUBREDDIT_LABELS[subreddit]
        filepath = os.path.join(raw_folder, filename)

        print(f"\nProcessing {filename} → Label: {label}")

        count = 0
        for post in tqdm(read_zst_file(filepath)):
            if count >= max_per_subreddit:
                break

            stats['total_seen'] += 1

            title = post.get('title', '')
            body = post.get('selftext', '')
            full_text = f"{title} {body}".strip()

            # Filter 1: Remove deleted/removed
            if body in ['[deleted]', '[removed]', '']:
                stats['deleted_removed'] += 1
                continue

            # Filter 2: Clean the text
            full_text_cleaned = clean_text(full_text)

            # Filter 3: Remove too short or too long
            if not is_quality_post(full_text_cleaned, min_words=30, max_words=500):
                if len(full_text_cleaned.split()) < 30:
                    stats['too_short'] += 1
                else:
                    stats['too_long'] += 1
                continue

            # Filter 4: Remove spam/job posts/irrelevant
            if is_spam(full_text_cleaned):
                stats['spam_filtered'] += 1
                continue

            # Filter 5: Must contain stress-related keywords
            if not has_stress_indicator(full_text_cleaned, label):
                stats['no_stress_indicator'] += 1
                continue

            all_data.append({
                'title': title,
                'text': body,
                'full_text': full_text_cleaned,
                'subreddit': subreddit,
                'stress_label': label
            })
            count += 1
            stats['kept'] += 1

        print(f"✅ Collected {count} posts from r/{subreddit}")

    # Save to CSV
    df = pd.DataFrame(all_data)
    output_path = os.path.join(output_folder, 'parsed_data.csv')
    df.to_csv(output_path, index=False, encoding='utf-8')

    # Print full report
    print(f"\n{'='*50}")
    print(f"📊 FILTERING REPORT (save this for your paper!)")
    print(f"{'='*50}")
    print(f"Total posts seen:          {stats['total_seen']:,}")
    print(f"Deleted/removed:           {stats['deleted_removed']:,}")
    print(f"Too short (<30 words):     {stats['too_short']:,}")
    print(f"Too long (>500 words):     {stats['too_long']:,}")
    print(f"Spam/irrelevant filtered:  {stats['spam_filtered']:,}")
    print(f"No stress indicator:       {stats['no_stress_indicator']:,}")
    print(f"✅ Final kept:             {stats['kept']:,}")
    print(f"\n📈 Label distribution:")
    print(df['stress_label'].value_counts())
    print(f"\n💾 Saved to {output_path}")

    return df

# Run it
if __name__ == "__main__":
    raw_folder = r"F:\UNIVERSITY\NU 3\semester 2\Machine Intelligence\Project\StressClassifier\data\raw"
    output_folder = r"F:\UNIVERSITY\NU 3\semester 2\Machine Intelligence\Project\StressClassifier\data\parsed"
    df = parse_all_files(raw_folder, output_folder, max_per_subreddit=15000)
# ```

# ---

# ## What's New in This Version

# | Filter | What It Removes |
# |---|---|
# | **Deleted/Removed** | Posts with `[deleted]` or `[removed]` |
# | **Too Short** | Posts under 30 words |
# | **Too Long** | Posts over 500 words |
# | **Spam Filter** | Job posts, ads, links, promotions |
# | **Stress Indicator** | Posts with no relevant keywords at all |

# ---

# ## 📝 Important for Your Paper

# The script prints a full **filtering report** like this:
# ```
# Total posts seen:          450,000
# Deleted/removed:           89,000
# Too short (<30 words):     120,000
# Spam/irrelevant filtered:  15,000
# No stress indicator:       80,000
# ✅ Final kept:             146,000
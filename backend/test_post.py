import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LIVE_URL = "https://aagroo-1.onrender.com/api/community/posts"

print("=" * 60)
print("  POSTING TO COMMUNITY & VERIFYING DATABASE UPDATES")
print("=" * 60)

# 1. Create a new post via API
payload = {
    "user_id": 1,
    "author_name": "Antigravity AI Agent",
    "location": "Thoothukudi, TN",
    "category": "Organic Farming",
    "content": "Live DB Verification Test: Successfully created community post in database!"
}

print(f"\n1. Sending POST request to: {LIVE_URL}")
response = requests.post(LIVE_URL, json=payload)
print(f"   HTTP Status Code: {response.status_code}")
post_result = response.json()
print("   Response Data:", post_result)

# 2. Retrieve posts from Database to verify insertion
print("\n2. Querying Database via GET request to verify insertion...")
get_response = requests.get(LIVE_URL)
all_posts = get_response.json().get("posts", [])

print(f"   Total Posts Found in Database: {len(all_posts)}")
print("\n--- COMMUNITY POSTS IN DATABASE ---")
found = False
for post in all_posts:
    print(f"ID: {post.get('id')} | Author: {post.get('author_name')} | Category: {post.get('category')}")
    print(f"Content: {post.get('content')}")
    print("-" * 50)
    if post.get("content") == payload["content"]:
        found = True

if found:
    print("\n✅ VERIFICATION SUCCESS: The new community post was successfully UPDATED and SAVED in the database!")
else:
    print("\n❌ VERIFICATION FAILED: Post not found in database.")

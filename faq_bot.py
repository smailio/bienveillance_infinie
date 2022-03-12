import praw
from praw.models import MoreComments
import os 
import httpx

azure_qa_host = os.getenv("AZURE_QA_HOST")
azure_qa_api_key = os.getenv("AZURE_API_KEY")
reddit_secret = os.getenv("REDDIT_SECRET")
reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
reddit_user_name = os.getenv("REDDIT_USER_NAME")
reddit_password = os.getenv("REDDIT_PASSWORD")
reddit_url = "https://www.reddit.com/r/SocialParis/comments/s0kjnk/13_janvier_2022_jeudi_bi%C3%A8re_weekly_paris_beer/"


reddit = praw.Reddit(
    client_id=reddit_client_id,
    client_secret=reddit_secret,
    user_agent="web:com.socialparis.faq:v0.0.0 (by u/bienveillanceinfinie)",
    username=reddit_user_name,
    password=reddit_password,
)

def post_question_azure(question):
    r = httpx.post(
        azure_qa_host, 
        json={'question': question}, 
        headers={"Authorization": f"EndpointKey {azure_qa_api_key}"}
    )
    print(r)
    return r.json()


def get_best_answer(answers):
    try:
        return answers["answers"][0]["answer"]
    except:
        print(answers)
        print("shitty andswr")
        return ""


def main():
    submission = reddit.submission(url=reddit_url)
    for top_level_comment in submission.comments:
        if isinstance(top_level_comment, MoreComments):
            continue
        comment_txt = top_level_comment.body
        # print(top_level_comment.body, top_level_comment.author)
        # print(top_level_comment.replies)
        if top_level_comment.author == 'Bricoto':
            print("hey bricoto")
            # top_level_comment.reply("salut !")
        if "?" in comment_txt and len(top_level_comment.replies) == 0:
            print(f"ask question {comment_txt}")
            top_level_comment.reply(get_best_answer(post_question_azure(comment_txt)))            

if __name__ == '__main__':
    main()

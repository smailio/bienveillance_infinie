import praw
from praw.models import MoreComments
import os 
import httpx
import re 
from datetime import datetime, timedelta
from calendar import THURSDAY
import logging 

logger = logging.getLogger("bienveillance_bot")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

azure_qa_host = os.getenv("AZURE_QA_HOST")
azure_qa_api_key = os.getenv("AZURE_API_KEY")
reddit_secret = os.getenv("REDDIT_SECRET")
reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
reddit_user_name = os.getenv("REDDIT_USER_NAME")
reddit_password = os.getenv("REDDIT_PASSWORD")
reddit_url = "https://www.reddit.com/r/SocialParis/comments/s0kjnk/13_janvier_2022_jeudi_bi%C3%A8re_weekly_paris_beer/"
jb_submissions_url = "https://www.reddit.com/r/SocialParis/search?q=flair_name%3A%22Jeudi%20Bi%C3%A8re%22"

logger.info(f"create reddit instance")
logger.info(f"azure_qa_host: {azure_qa_host}")
logger.info(f"reddit_client_id: {reddit_client_id}")
reddit = praw.Reddit(
    client_id=reddit_client_id,
    client_secret=reddit_secret,
    user_agent="web:com.socialparis.faq:v0.0.0 (by u/bienveillanceinfinie)",
    username=reddit_user_name,
    password=reddit_password,
)
logger.info("reddit instance created !")

def post_question_azure(question):
    """
    This is the function where the magic happens, we use the azure Q&A api that we configured 
    with the JB FAQ.
    """
    r = httpx.post(
        azure_qa_host, 
        json={'question': question}, 
        headers={"Authorization": f"EndpointKey {azure_qa_api_key}"}
    )
    return r.json()


def select_best_answer(answers_resp):
    try:
        answers = answers_resp["answers"]
        answers_sorted_by_score = list(sorted(answers, key=lambda a: a["score"], reverse=True))
        answer_with_highest_score = answers_sorted_by_score[0]
        if answer_with_highest_score["score"] < 70:
            logger.info(f"score too low for this {answer_with_highest_score}")
            return ""
        logger.info(f"best answer : {answer_with_highest_score['answer']}")
        logger.info(f"best answer score : {answer_with_highest_score['score']}")
        return answer_with_highest_score["answer"]
    except Exception as e:
        logger.error(f"shitty azure answers : {answers_resp}")
        logger.error(e)
        return ""

def get_last_jb_submission():

    def extract_date_from_titile(jb_submission):
        m = re.search('\[(.+)\].*', jb_submission.title)
        if not m:
            raise Exception(f"couldnt extract date from title {jb_submission.title} {jb_submission.url}")
        date_txt = m.group(1)
        import locale
        locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8") # french
        jb_date = datetime.strptime(date_txt, "%d %B %Y")
        return jb_date

    def is_next_thursday(jb_date):
        """
        The date must between last thursday and next thursday 
        """
        today = datetime.now()
        nb_days_untill_next_thursday = (today.weekday() + THURSDAY) % 7
        next_thursday = today + timedelta(days=nb_days_untill_next_thursday)
        logger.info(f"check {jb_date.date()} == {next_thursday.date()} {jb_date.date() == next_thursday.date()}")

        return jb_date.date() == next_thursday.date()

    submissions = reddit.subreddit('SocialParis').search('flair:"Jeudi Bière"', limit=12)
    
    # latest submission is not always the first returned so we need to sort by date
    if submissions:
        submissions = list(submissions)
        submissions = sorted(submissions, key=extract_date_from_titile, reverse=True)
        jb_sumbission = submissions[0]
        logger.info(f"submission title : {jb_sumbission.title}")
        jb_date = extract_date_from_titile(jb_sumbission)
        logger.info(f"jb date from title : {jb_date}")
        if is_next_thursday(jb_date):
            return jb_sumbission
        else:
            logger.info("The submission for this week's JB is not out yet")
            return None
    else:
        logger.info("No sumbission found")
        return None


def main():
    jb_submission = get_last_jb_submission()
    if not jb_submission:
        return
    for top_level_comment in jb_submission.comments:
        if isinstance(top_level_comment, MoreComments):
            continue
        comment_txt = top_level_comment.body
        if "?" in comment_txt and len(top_level_comment.replies) == 0:
            logger.info(f"found question {comment_txt}")
            azure_answers = post_question_azure(comment_txt)
            logger.info(f"azure_answers received")
            best_answer = select_best_answer(azure_answers)
            if best_answer:
                logger.info("replying... ")
                top_level_comment.reply(best_answer)  
                logger.info("reply success !")
    else:
        logger.info("No comments yet on this week jb")          

if __name__ == '__main__':
    main()

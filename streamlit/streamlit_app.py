import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from collections import Counter
import re
import nltk
import json

nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords

st.set_page_config(page_title='Survey Dashboard', layout='wide', page_icon="📊")

@st.cache_data
def load_data(file_path, separator=',', encoding='utf-8'):
    try:
        df = pd.read_csv(file_path, sep=separator, encoding=encoding)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()
    
def load_comments_json(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        comments_data = []
        for post in data:
            for comment in post['comments']:
                comments_data.append({
                    'post_link': post['post_link'],
                    'username': comment['username'],
                    'comment': comment['comment'],
                    'is_reply': comment['is_reply'],
                    'reply_to': comment['reply_to'],
                    'timestamp': comment['timestamp']
                })
        return pd.DataFrame(comments_data)
    except Exception as e:
        st.error(f"Error loading comments data: {e}")
        return pd.DataFrame()
    
def display_instagram_content(post_link, likes_count, comments_count):
    if '/reel/' in post_link:
        content_type = 'reel'
    else:
        content_type = 'post'
        
    try:
        container = st.container()
        
        with container:
            embed_html = f"""
            <div style="width: 100%; max-width: 550px; margin: 0 auto;">
                <iframe 
                    src="https://www.instagram.com/{content_type}/{post_link.split('/')[-2]}/embed" 
                    width="100%" 
                    height="450" 
                    frameborder="0" 
                    scrolling="no" 
                    allowtransparency="true"
                    style="border-radius: 3px; border: 1px solid var(--st-color-border-light);">
                </iframe>
            </div>
            """
            st.components.v1.html(embed_html, height=450)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(
                    f"""
                    <div style="text-align: center;">
                        <p style="font-size: 1.2em; margin-bottom: 0;">👍 {likes_count:,}</p>
                        <p style="color: var(--st-color-secondary); margin-top: 0;">Likes</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col2:
                st.markdown(
                    f"""
                    <div style="text-align: center;">
                        <p style="font-size: 1.2em; margin-bottom: 0;">💬 {comments_count:,}</p>
                        <p style="color: var(--st-color-secondary); margin-top: 0;">Comments</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
    except Exception as e:
        st.warning("Unable to load Instagram content directly.")
        
        st.markdown(f"🔗 [View {content_type.title()} on Instagram]({post_link})")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
                <div style="text-align: center;">
                    <p style="font-size: 1.2em; margin-bottom: 0;">👍 {likes_count:,}</p>
                    <p style="color: var(--st-color-secondary); margin-top: 0;">Likes</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""
                <div style="text-align: center;">
                    <p style="font-size: 1.2em; margin-bottom: 0;">💬 {comments_count:,}</p>
                    <p style="color: var(--st-color-secondary); margin-top: 0;">Comments</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
def main():
    st.sidebar.title("Sidebar Options")

    post_data_df_path = 'streamlit/data/post_data_1_df.csv'
    sentiment_df_path = 'streamlit/data/sentiment_2_df.csv'

    post_data_df = load_data(post_data_df_path)
    sentiment_df = load_data(sentiment_df_path)

    filtered_post_data_df = post_data_df[['username', 'post_link', 'likes_count', 'comments_count']]


    usernames = ["All Posts"] + filtered_post_data_df['username'].unique().tolist()
    selected_username = st.sidebar.selectbox(
        "Choose post to display:",
        usernames,
        index=0
    )
    
    selected_comment_type = st.sidebar.selectbox(
        "Choose comment type",
        ['All', 'non-reply'],
        index=0
    )

    if selected_username == "All Posts":
        displayed_filtered_post_data_df = post_data_df
        filtered_sentiment_df = sentiment_df
    else:
        displayed_filtered_post_data_df = post_data_df[post_data_df['username'] == selected_username]
        filtered_sentiment_df = sentiment_df[sentiment_df['post_username'] == selected_username]
   
    if selected_comment_type == 'non-reply':
        filtered_sentiment_df = filtered_sentiment_df[filtered_sentiment_df['Comment'].str[0] != '@']

    st.title("Sebelas Rasa Sentiment Analysis")

    col1, col2 = st.columns([3, 2])

    with col1:
        if selected_username != "All Posts":
            post_link = displayed_filtered_post_data_df.iloc[0]['post_link']
            likes_count = displayed_filtered_post_data_df.iloc[0]['likes_count']
            comments_count = displayed_filtered_post_data_df.iloc[0]['comments_count']
            display_instagram_content(post_link, likes_count, comments_count)
        else:
            total_posts = len(displayed_filtered_post_data_df)
            total_likes = displayed_filtered_post_data_df['likes_count'].sum()
            total_comments = displayed_filtered_post_data_df['comments_count'].sum()
            
            st.markdown("""
            <div style='padding: 20px; border-radius: 5px; text-align: center; font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin-top: 40px;'>
                <h2>Overall Statistics</h2>
                <div style='display: flex; justify-content: space-around; margin-top: 40px;'>
                    <div>
                        <h3>Posts</h3>
                        <p style='font-size: 24px;'>{:,}</p>
                    </div>
                    <div>
                        <h3>Likes</h3>
                        <p style='font-size: 24px;'>{:,}</p>
                    </div>
                    <div>
                        <h3>Comments</h3>
                        <p style='font-size: 24px;'>{:,}</p>
                    </div>
                </div>
            </div>
            """.format(total_posts, total_likes, total_comments), unsafe_allow_html=True)
    with col2:
        labels = ['positive', 'neutral', 'negative']
        total_pos = filtered_sentiment_df[filtered_sentiment_df['Sentiment'] == labels[0]].shape[0]
        total_neu = filtered_sentiment_df[filtered_sentiment_df['Sentiment'] == labels[1]].shape[0]
        total_neg = filtered_sentiment_df[filtered_sentiment_df['Sentiment'] == labels[2]].shape[0]

        fig = px.pie(
            names=labels,
            values=[total_pos, total_neu, total_neg],
            title="Comment Sentiment Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig)

    with st.container():
        st.title("Comments")
        columns_to_exclude = ['post_username']
        display_columns = [col for col in filtered_sentiment_df.columns if col not in columns_to_exclude]
        st.dataframe(filtered_sentiment_df[display_columns], use_container_width=True)

if __name__ == "__main__":
    main()
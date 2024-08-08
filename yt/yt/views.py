import boto3
from botocore.exceptions import NoCredentialsError
from pytube import YouTube
from pytube.exceptions import RegexMatchError
from django.shortcuts import render
import os
from moviepy.editor import VideoFileClip
from decouple import config


# AWS S3 settings
S3_BUCKET_NAME = config('S3_BUCKET_NAME')
S3_REGION_NAME = config('S3_REGION_NAME')  
S3_ACCESS_KEY = config('S3_ACCESS_KEY')
S3_SECRET_KEY = config('S3_SECRET_KEY')

def homePage(request):
    return render(request, 'index.html')

def trim_video(input_path, output_path, start_time, end_time):
    # Load the video file
    with VideoFileClip(input_path) as video:
        # Trim the video
        trimmed_video = video.subclip(start_time, end_time)
        # Save the trimmed video to a new file
        trimmed_video.write_videofile(output_path, codec='libx264')

def upload_to_s3(file_path, bucket_name, region_name, access_key, secret_key):
    s3_client = boto3.client('s3', region_name=region_name,
                             aws_access_key_id=access_key,
                             aws_secret_access_key=secret_key)
    try:
        file_name = os.path.basename(file_path)
        s3_client.upload_file(file_path, bucket_name, file_name)
        public_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{file_name}"
        return public_url
    except FileNotFoundError:
        print("The file was not found")
        return None
    except NoCredentialsError:
        print("Credentials not available")
        return None

def views(request):
    if request.method == 'POST':
        url = request.POST.get('link')
        start_time = int(request.POST.get('start_time', 0))
        end_time = int(request.POST.get('end_time', 10))
        print("url: ", url)
        try:
            yt = YouTube(url)
            print("yt: ", yt)

            # Get the highest resolution stream
            stream = yt.streams.get_highest_resolution()
            print("stream: ", stream)

            # Define the download path
            download_path = r'C:\Users\Abdul Manaf\Desktop\yt-down\temp\temp'
            if not os.path.exists(download_path):
                os.makedirs(download_path)

            # Download the video
            video_file_name = f"{yt.title}.mp4"
            video_file_path = os.path.join(download_path, video_file_name)
            stream.download(output_path=download_path, filename=video_file_name)
            print(f"Video downloaded to: {video_file_path}")

            # Define the trimmed video path
            trimmed_video_file_name = f"trimmed_{yt.title}.mp4"
            trimmed_video_file_path = os.path.join(download_path, trimmed_video_file_name)

            # Trim the video
            trim_video(video_file_path, trimmed_video_file_path, start_time, end_time)
            print(f"Trimmed video saved to: {trimmed_video_file_path}")

            # Upload the trimmed video to S3
            s3_url = upload_to_s3(trimmed_video_file_path, S3_BUCKET_NAME, S3_REGION_NAME, S3_ACCESS_KEY, S3_SECRET_KEY)
            print(f"Uploaded to S3: {s3_url}")

            # Provide the download link and file path
            new_url = stream.url
            video_file_url = f"/path-to-your-media/{video_file_name}"  # Update this as needed
            trimmed_video_file_url = s3_url

            return render(request, 'index.html', {
                'new_url': new_url,
                'video_file_url': video_file_url,
                'trimmed_video_file_url': trimmed_video_file_url
            })
        except RegexMatchError:
            new_url = None
            video_file_url = None
            trimmed_video_file_url = None
            print("RegexMatchError: Could not find match.")
        except Exception as e:
            new_url = None
            video_file_url = None
            trimmed_video_file_url = None
            print(f"Exception: {e}")
        print("Final new_url: ", new_url)
        return render(request, 'index.html', {
            'new_url': new_url,
            'video_file_url': video_file_url,
            'trimmed_video_file_url': trimmed_video_file_url
        })
    else:
        return render(request, 'index.html')

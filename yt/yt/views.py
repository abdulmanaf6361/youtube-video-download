import boto3
from botocore.exceptions import NoCredentialsError
from django.shortcuts import render
import os
import ffmpeg
from decouple import config
import yt_dlp
from django.views.decorators.csrf import csrf_exempt

# AWS S3 settings
S3_BUCKET_NAME = config('S3_BUCKET_NAME')
S3_REGION_NAME = config('S3_REGION_NAME')
S3_ACCESS_KEY = config('S3_ACCESS_KEY')
S3_SECRET_KEY = config('S3_SECRET_KEY')

def homePage(request):
    return render(request, 'index.html')

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

def trim_video(input_path, output_path, start_time, end_time):
    if not os.path.isfile(input_path):
        print(f"Error: File {input_path} does not exist.")
        return
    try:
        ffmpeg.input(input_path, ss=start_time, to=end_time).output(output_path, codec='libx264').run()
    except ffmpeg.Error as e:
        print(f"Error in trimming video: {e.stderr.decode()}")

def time_to_seconds(time_str):
    """Convert HH:MM:SS time string to seconds."""
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s

@csrf_exempt
def views(request):
    if request.method == 'POST':
        url = request.POST.get('link')
        start_time_str = request.POST.get('start_time', '00:00:00')
        end_time_str = request.POST.get('end_time', '00:00:10')
        
        # Convert time strings to seconds
        start_time = time_to_seconds(start_time_str)
        end_time = time_to_seconds(end_time_str)
        download_path = '/youtube-video-download/yt/'
        downloaded_filename = os.path.join(download_path, 'a.mp4')
        trimmed_filename = os.path.join(download_path, 'trimmed_a.mp4')
        new_url = None
        trimmed_video_file_url = None
        
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': downloaded_filename,
                'nocheckcertificate': True,
                'continuedl': False  # Disable resuming downloads
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
                # Verify if the file exists after downloading
                if not os.path.isfile(downloaded_filename):
                    raise FileNotFoundError(f"Downloaded file {downloaded_filename} does not exist.")
                
                # Trim the video
                print(f"Trimming video from {downloaded_filename} to {trimmed_filename}")
                trim_video(downloaded_filename, trimmed_filename, start_time, end_time)
                
                # Upload to S3
                s3_url = upload_to_s3(trimmed_filename, S3_BUCKET_NAME, S3_REGION_NAME, S3_ACCESS_KEY, S3_SECRET_KEY)
                print(f"Uploaded to S3: {s3_url}")
                trimmed_video_file_url = s3_url

        except Exception as e:
            new_url = None
            print(f"Exception: {e}")

        finally:
            # Delete the original and trimmed files after processing
            if os.path.isfile(downloaded_filename):
                os.remove(downloaded_filename)
                print(f"Deleted file: {downloaded_filename}")
            if os.path.isfile(trimmed_filename):
                os.remove(trimmed_filename)
                print(f"Deleted file: {trimmed_filename}")
        
        print("Final new_url: ", new_url)
        return render(request, 'index.html', {'new_url': new_url, 'trimmed_video_file_url': trimmed_video_file_url})
    else:
        return render(request, 'index.html')

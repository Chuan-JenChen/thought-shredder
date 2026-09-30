@echo off
cd /d "C:\Users\JDA\Desktop\ai_video_project"
call C:\Anaconda\Scripts\activate.bat ai_anchor_free
python daily_pipeline.py
pause
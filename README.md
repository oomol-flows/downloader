# OOMOL Downloader 🚀

A powerful, user-friendly file download toolkit for OOMOL workflows that makes downloading files from the internet simple and reliable.

## What is OOMOL Downloader?

OOMOL Downloader is a collection of pre-built workflow blocks (components) that help you download files from the internet efficiently. Whether you need to download a single file, multiple files, or entire folders worth of content, this toolkit has you covered.

**Perfect for:**
- Content creators downloading resources
- Data analysts gathering datasets
- Researchers collecting files for projects
- Anyone who needs to download files reliably and efficiently

## Available Workflow Blocks

### 🎯 Single File Downloader
**What it does:** Downloads one file from a URL to your computer

**When to use it:**
- Download a single document, image, or video
- Get the latest version of a file from a website
- Save a specific resource for offline use

**Key features:**
- Automatic resume if download is interrupted
- Choose where to save the file
- Handle existing files (skip or replace)
- Real-time progress tracking

---

### 📁 Folder Downloader
**What it does:** Downloads multiple files and organizes them in a folder

**When to use it:**
- Download a collection of related files
- Batch download images or documents
- Organize downloads into specific folders
- Clean up and prepare folder structure

**Key features:**
- Download multiple files at once
- Automatic folder organization
- Skip or replace existing files
- Option to clean target folder before downloading

---

### 🔗 URL to File Converter
**What it does:** Takes any URL and automatically downloads it as a file

**When to use it:**
- Quick download without specifying file details
- Auto-detect file names from URLs
- Simple drag-and-drop style downloading
- Handle various file types automatically

**Key features:**
- Automatic file name detection
- Smart folder management
- Flexible file naming options
- Handle different URL formats

---

### ⚡ Advanced Multi-File Downloader (Core Engine)
**What it does:** The powerful engine behind all downloaders with advanced controls

**When to use it:**
- Need maximum control over download process
- Handle complex download scenarios
- Fine-tune performance settings
- Monitor detailed download events

**Advanced features:**
- **Multi-threading:** Download several files simultaneously for speed
- **Smart retry:** Automatically retry failed downloads with customizable delays
- **Connection management:** Optimize download performance with window width control
- **Segment downloads:** Break large files into chunks for reliability
- **Timeout control:** Set how long to wait for slow connections
- **Event monitoring:** Get detailed notifications about download progress and failures

## How Download Performance Works

### 🚀 Speed Optimization
- **Concurrent Downloads:** Set `threads_count` to download multiple files at once
- **Chunk Size:** Adjust `once_fetch_size` to optimize for your internet speed
- **Connection Windows:** Use `window_width` to manage connection efficiency

### 🔄 Reliability Features
- **Auto Resume:** If a download fails, it automatically picks up where it left off
- **Smart Retry:** Configure `retry_times` and `retry_sleep` to handle temporary network issues
- **Failure Handling:** Choose to continue with other files or stop on first error

### 📊 Progress Tracking
- Real-time progress updates for each file
- Success and failure notifications
- Detailed error reporting when things go wrong

## Common Use Cases

### For Content Creators
- Download stock images and videos for projects
- Get the latest templates and resources
- Batch download fonts or design assets

### For Researchers & Students
- Download research papers and datasets
- Collect reference materials for projects
- Archive web content for offline study

### For Data Analysis
- Download CSV files and databases
- Collect API responses as files
- Gather training data for machine learning

### For General Users
- Backup important files from cloud services
- Download software updates and installers
- Collect media files for personal projects

## Getting Started

1. **Choose the right block** for your needs:
   - Single file → Use "Single File Downloader"
   - Multiple files → Use "Folder Downloader"
   - Quick downloads → Use "URL to File Converter"
   - Advanced needs → Use "Advanced Multi-File Downloader"

2. **Configure your settings:**
   - Set where to save files
   - Choose what happens with existing files
   - Adjust performance if needed

3. **Run your workflow** and monitor progress in real-time

## Why Choose OOMOL Downloader?

✅ **Reliable:** Built-in retry mechanisms and resume capability
✅ **Fast:** Multi-threaded downloads for maximum speed
✅ **Flexible:** Works with any file type and URL format
✅ **User-Friendly:** No coding required, just configure and run
✅ **Transparent:** Clear progress updates and error messages
✅ **Efficient:** Smart resource management and optimization

## Technical Specifications

- **Supported Protocols:** HTTP, HTTPS
- **File Types:** Any downloadable file format
- **Performance:** Up to 50+ concurrent downloads (configurable)
- **Resume Support:** Automatic checkpoint recovery
- **Error Handling:** Comprehensive retry and fallback mechanisms
- **Progress Tracking:** Real-time updates and completion notifications

---

*OOMOL Downloader is part of the OOMOL ecosystem - making complex tasks simple through visual workflows.*
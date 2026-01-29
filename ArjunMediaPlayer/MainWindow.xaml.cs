using System;
using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows. Input;
using Microsoft.Win32;
using System.IO;
using System.Windows.Media;
using System.Windows.Shapes;
using System.Windows.Threading;
using System.Windows.Interop;

// Alias the Path class to avoid ambiguity
using ShapePath = System.Windows.Shapes.Path;
using IoPath = System.IO.Path;

namespace ArjunMediaPlayer
{
    public partial class MainWindow : Window
    {
        private bool isPlaying = false;
        private bool isMuted = false;
        private bool isFullscreen = false;
        private DispatcherTimer? uiUpdateTimer;
        private DateTime lastUserActionTime = DateTime.MinValue;
        private const int USER_ACTION_COOLDOWN_MS = 500; // 500ms cooldown after user action
        private double previousPosition = -1;
        private DateTime previousCheckTime = DateTime.MinValue;
        
        public MainWindow()
        {
            Debug.WriteLine("MainWindow constructor called");
            InitializeComponent();
            InitializeMediaElement();
            SetupUIUpdateTimer();
        }

        private void InitializeMediaElement()
        {
            // Subscribe to media events
            mediaElement.MediaOpened += MediaElement_MediaOpened;
            mediaElement.MediaEnded += MediaElement_MediaEnded;
            mediaElement.MediaFailed += MediaElement_MediaFailed;
            
            // Initially show the drop zone when no media is loaded
            dropZone.Visibility = Visibility.Visible;
            centerPlayButton.Visibility = Visibility.Collapsed;
            
            // Set initial button icons
            UpdatePlayPauseIcon();
            UpdateVolumeIcon();
        }

        private void SetupUIUpdateTimer()
        {
            uiUpdateTimer = new System.Windows.Threading.DispatcherTimer();
            uiUpdateTimer.Interval = TimeSpan.FromMilliseconds(200); // Update more frequently for smoother experience
            uiUpdateTimer.Tick += UIUpdateTimer_Tick;
            uiUpdateTimer.Start();
        }

        private void MediaElement_MediaOpened(object sender, RoutedEventArgs e)
        {
            // Update UI when media is loaded
            totalTimeText.Text = TimeSpan.FromSeconds(mediaElement.NaturalDuration.TimeSpan.TotalSeconds).ToString(@"hh\:mm\:ss");
            timelineSlider.Maximum = mediaElement.NaturalDuration.TimeSpan.TotalSeconds;

            // Hide drop zone and initially show play button
            dropZone.Visibility = Visibility.Collapsed;
            centerPlayButton.Visibility = Visibility.Visible;
            isPlaying = false; // Initially not playing until user presses play
            UpdatePlayPauseIcon(); // Use method to update icon

            // Update file name display
            string fileName = IoPath.GetFileName(mediaElement.Source.ToString());
            fileNameText.Text = fileName;

            // Show control bar briefly when media loads
            ShowControlBar();
        }

        private void MediaElement_MediaEnded(object sender, RoutedEventArgs e)
        {
            // Reset play button when media ends
            isPlaying = false;
            UpdatePlayPauseIcon();
        }

        private void MediaElement_MediaFailed(object? sender, ExceptionRoutedEventArgs e)
        {
            MessageBox.Show("Error loading media file.", "Media Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }

        // Menu Event Handlers
        // Main menu item handlers for logging and feedback
        private void MainMenuMedia_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("MainMenuMedia_Click called - Media menu opened");
        }

        private void MainMenuPlayback_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("MainMenuPlayback_Click called - Playback menu opened");
        }

        private void MainMenuAudio_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("MainMenuAudio_Click called - Audio menu opened");
        }

        private void MainMenuVideo_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("MainMenuVideo_Click called - Video menu opened");
        }

        private void MainMenuSubtitle_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("MainMenuSubtitle_Click called - Subtitle menu opened");
        }

        private void MainMenuTools_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("MainMenuTools_Click called - Tools menu opened");
        }

        private void MainMenuView_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("MainMenuView_Click called - View menu opened");
        }

        private void MainMenuHelp_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("MainMenuHelp_Click called - Help menu opened");
        }

        private void MenuItem_SubmenuOpened(object sender, RoutedEventArgs e)
        {
            if (sender is MenuItem menuItem)
            {
                System.Console.WriteLine($"Submenu opened: {menuItem.Header}");
            }
        }

        private void MenuItem_SubmenuClosed(object sender, RoutedEventArgs e)
        {
            if (sender is MenuItem menuItem)
            {
                System.Console.WriteLine($"Submenu closed: {menuItem.Header}");
            }
        }

        private void OpenFile_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("OpenFile_Click called");
            OpenFileDialog openFileDialog = new OpenFileDialog();
            openFileDialog.Filter = "Media Files|*.mp4;*.mov;*.avi;*.mpeg;*.wmv;*.ts;*.mkv;*.flv;*.m4v|" +
                                   "Video Files|*.mp4;*.mov;*.avi;*.mpeg;*.wmv;*.ts|" +
                                   "Audio Files|*.mp3;*.wav;*.wma;*.aac;*.flac|" +
                                   "All Files|*.*";

            if (openFileDialog.ShowDialog() == true)
            {
                LoadMedia(openFileDialog.FileName);
            }
        }

        private void OpenUrl_Click(object sender, RoutedEventArgs e)
        {
            // For now, just show a simple dialog to enter URL
            var urlDialog = new UrlInputDialog();
            if (urlDialog.ShowDialog() == true)
            {
                LoadMedia(urlDialog.Url);
            }
        }

        private void Exit_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("Exit_Click called");
            Application.Current.Shutdown();
        }

        private void Play_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("Play_Click called");
            if (mediaElement.Source != null)
            {
                mediaElement.Play();
                isPlaying = true;
                lastUserActionTime = DateTime.Now; // Record user action
                System.Console.WriteLine("Media played, isPlaying set to true");
                UpdatePlayPauseIcon();
                ShowControlBar(); // Show controls when playing
            }
            else
            {
                System.Console.WriteLine("No media source in Play_Click");
            }
        }

        private void Pause_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("Pause_Click called");
            if (mediaElement.Source != null)
            {
                mediaElement.Pause();
                isPlaying = false;
                lastUserActionTime = DateTime.Now; // Record user action
                System.Console.WriteLine("Media paused, isPlaying set to false");
                UpdatePlayPauseIcon();
                ShowControlBar(); // Show controls when paused
            }
            else
            {
                System.Console.WriteLine("No media source in Pause_Click");
            }
        }

        private void Stop_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("Stop_Click called");
            if (mediaElement.Source != null)
            {
                mediaElement.Stop();
                isPlaying = false;
                lastUserActionTime = DateTime.Now; // Record user action
                System.Console.WriteLine("Media stopped, isPlaying set to false");
                UpdatePlayPauseIcon();
                ShowControlBar(); // Show controls when stopped
            }
            else
            {
                System.Console.WriteLine("No media source in Stop_Click");
            }
        }

        private void Previous_Click(object sender, RoutedEventArgs e)
        {
            // Navigate to previous position in media (30 seconds back)
            mediaElement.Position = TimeSpan.FromSeconds(Math.Max(0, mediaElement.Position.TotalSeconds - 30));
        }

        private void Mute_Click(object sender, RoutedEventArgs e)
        {
            isMuted = !isMuted;
            mediaElement.IsMuted = isMuted;
            UpdateVolumeIcon();
        }

        private void AudioTracks_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("AudioTracks_Click called");
            // Placeholder for audio track selection - in a real implementation, this would show audio tracks
            // For now, just show a message
            if (mediaElement.Source != null)
            {
                // In a real implementation, we would enumerate audio tracks
                // For now, just show a simple message
                MessageBox.Show("Audio track selection would appear here.\nCurrently loaded media has audio tracks available.",
                    "Audio Tracks", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            else
            {
                MessageBox.Show("No media loaded. Please load a media file first.",
                    "No Media", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
        }

        private void AspectRatio_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("AspectRatio_Click called");
            // Toggle aspect ratio between different modes
            if (mediaElement.Stretch == Stretch.Uniform)
            {
                mediaElement.Stretch = Stretch.Fill;  // Fill the entire space
            }
            else if (mediaElement.Stretch == Stretch.Fill)
            {
                mediaElement.Stretch = Stretch.UniformToFill;  // Uniform but fill
            }
            else
            {
                mediaElement.Stretch = Stretch.Uniform;  // Back to default
            }
        }

        private void Crop_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("Crop_Click called");
            // Placeholder for crop options - in a real implementation, this would allow cropping
            MessageBox.Show("Crop options would appear here.\nThis feature allows you to crop the video display area.",
                "Crop", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void LoadSubtitle_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("LoadSubtitle_Click called");
            // Placeholder for subtitle loading
            OpenFileDialog openFileDialog = new OpenFileDialog();
            openFileDialog.Filter = "Subtitle Files|*.srt;*.vtt;*.ass;*.ssa|" +
                                   "All Files|*.*";

            if (openFileDialog.ShowDialog() == true)
            {
                // In a real implementation, we would load the subtitle file
                // For now, just show a message
                MessageBox.Show($"Subtitle loaded: {IoPath.GetFileName(openFileDialog.FileName)}\nSubtitle functionality would be implemented in a full version.",
                    "Subtitle Loaded", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void SubtitleTracks_Click(object sender, RoutedEventArgs e)
        {
            // Placeholder for subtitle track selection
            if (mediaElement.Source != null)
            {
                // In a real implementation, we would enumerate subtitle tracks
                MessageBox.Show("Subtitle track selection would appear here.\nCurrently loaded media has subtitle tracks available.",
                    "Subtitles", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            else
            {
                MessageBox.Show("No media loaded. Please load a media file first.",
                    "No Media", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
        }

        private void Preferences_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("Preferences_Click called");
            MessageBox.Show("Preferences dialog would appear here.\nThis would allow you to configure player settings.",
                "Preferences", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void Fullscreen_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("Fullscreen_Click called");
            ToggleFullscreen();
        }

        private void AlwaysOnTop_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("AlwaysOnTop_Click called");
            Topmost = !Topmost;
        }

        private void About_Click(object sender, RoutedEventArgs e)
        {
            System.Console.WriteLine("About_Click called");
            MessageBox.Show("Arjun Media Player\nVersion 1.0\nA Netflix-like media player with VLC features.",
                "About Arjun Media Player", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        // Main Controls Event Handlers
        private void CenterPlay_Click(object sender, RoutedEventArgs e)
        {
            TogglePlayPause();
        }

        private void PlayPause_Click(object sender, RoutedEventArgs e)
        {
            TogglePlayPause();
        }

        private void TogglePlayPause()
        {
            System.Console.WriteLine($"TogglePlayPause called. Current isPlaying: {isPlaying}");

            if (mediaElement.Source == null)
            {
                System.Console.WriteLine("No media source, opening file dialog");
                OpenFile_Click(this, new RoutedEventArgs()); // If no media loaded, prompt to open
                return;
            }

            if (isPlaying)
            {
                System.Console.WriteLine("Pausing media");
                mediaElement.Pause();
                isPlaying = false;
            }
            else
            {
                System.Console.WriteLine("Playing media");
                mediaElement.Play();
                isPlaying = true;
            }
            // Record the time of this user action
            lastUserActionTime = DateTime.Now;
            System.Console.WriteLine($"After toggle, isPlaying: {isPlaying}");
            UpdatePlayPauseIcon();
            ShowControlBar(); // Show controls when toggling play/pause

            // Force update the UI immediately after user action
            if (isPlaying)
            {
                centerPlayButton.Visibility = Visibility.Collapsed;
                System.Console.WriteLine("Set centerPlayButton to Collapsed");
            }
            else
            {
                centerPlayButton.Visibility = Visibility.Visible;
                System.Console.WriteLine("Set centerPlayButton to Visible");
            }
        }

        private void Info_Click(object sender, RoutedEventArgs e)
        {
            // Placeholder for info/about functionality
            MessageBox.Show("Media information would appear here.", "Media Info", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void Next_Click(object sender, RoutedEventArgs e)
        {
            // Navigate to next position in media (30 seconds forward)
            mediaElement.Position = TimeSpan.FromSeconds(
                Math.Min(mediaElement.NaturalDuration.TimeSpan.TotalSeconds,
                         mediaElement.Position.TotalSeconds + 30));
        }

        private void Folder_Click(object sender, RoutedEventArgs e)
        {
            // Placeholder for folder browsing functionality
            MessageBox.Show("Folder browser would appear here.", "Browse Folder", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void Rewind_Click(object sender, RoutedEventArgs e)
        {
            // Rewind 10 seconds
            mediaElement.Position = TimeSpan.FromSeconds(
                Math.Max(0, mediaElement.Position.TotalSeconds - 10));
            ShowControlBar(); // Show controls briefly
        }

        private void FastForward_Click(object sender, RoutedEventArgs e)
        {
            // Fast forward 10 seconds
            mediaElement.Position = TimeSpan.FromSeconds(
                Math.Min(mediaElement.NaturalDuration.TimeSpan.TotalSeconds, 
                         mediaElement.Position.TotalSeconds + 10));
            ShowControlBar(); // Show controls briefly
        }

        // Sliders Event Handlers
        private void VolumeSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            mediaElement.Volume = volumeSlider.Value / 100.0;
            UpdateVolumeIcon();
        }

        private bool isDraggingSlider = false;

        private void TimelineSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            // Update media position when slider value changes (whether from dragging or clicking)
            // Only update if we're not in a user drag operation to prevent conflicts
            if (!isDraggingSlider)
            {
                // For clicks or programmatic changes, update the media position
                mediaElement.Position = TimeSpan.FromSeconds(timelineSlider.Value);
            }
        }

        private void TimelineSlider_PreviewMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            // Set the dragging flag when user starts dragging the slider thumb
            isDraggingSlider = true;

            // Pause the media during seeking for better UX
            if (isPlaying)
            {
                mediaElement.Pause();
                System.Console.WriteLine("Paused media during seeking (drag started)");
            }
        }

        private void TimelineSlider_PreviewMouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            // Update position one final time when releasing the slider
            mediaElement.Position = TimeSpan.FromSeconds(timelineSlider.Value);
            System.Console.WriteLine($"Updated media position to: {TimeSpan.FromSeconds(timelineSlider.Value)}");

            // Resume playback if it was playing before seeking
            if (isPlaying)
            {
                mediaElement.Play();
                System.Console.WriteLine("Resumed media playback");
            }

            // Reset the dragging flag
            isDraggingSlider = false;
        }

        private void TimelineSlider_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            System.Console.WriteLine("TimelineSlider_MouseLeftButtonDown called");
            // Handle clicking anywhere on the timeline to jump to that position
            // Only if not currently dragging
            if (sender is Slider slider && !isDraggingSlider)
            {
                // Calculate the position based on click location
                Point clickPoint = e.GetPosition(slider);
                double clickX = clickPoint.X;
                double totalWidth = slider.ActualWidth;

                System.Console.WriteLine($"Slider click: clickX={clickX}, totalWidth={totalWidth}");

                // Calculate the percentage of the way across the slider
                double percentage = clickX / totalWidth;

                System.Console.WriteLine($"Calculated percentage: {percentage}");

                // Calculate the new value based on the percentage
                double newValue = slider.Minimum + (percentage * (slider.Maximum - slider.Minimum));

                System.Console.WriteLine($"Calculated newValue: {newValue}");

                // Ensure the value is within bounds
                newValue = Math.Max(slider.Minimum, Math.Min(slider.Maximum, newValue));

                System.Console.WriteLine($"Clamped newValue: {newValue}");

                // Update the slider value and media position
                slider.Value = newValue;
                mediaElement.Position = TimeSpan.FromSeconds(newValue);

                System.Console.WriteLine($"Updated slider value to: {newValue}, media position to: {TimeSpan.FromSeconds(newValue)}");

                // Explicitly update the UI to reflect the change
                UpdatePlayPauseIcon();
            }
        }

        // Drag and Drop Support
        private void Media_DragEnter(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                e.Effects = DragDropEffects.Copy;
                ShowControlBar(); // Show controls when dragging
            }
            else
            {
                e.Effects = DragDropEffects.None;
            }
        }

        private void Media_Drop(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                string[] files = (string[])e.Data.GetData(DataFormats.FileDrop);
                if (files.Length > 0 && files[0] != null)
                {
                    LoadMedia(files[0]);
                }
            }
        }

        private void LoadMedia(string? path)
        {
            if (string.IsNullOrEmpty(path)) return;

            try
            {
                mediaElement.Source = new Uri(path);
                mediaElement.Play();
                isPlaying = true;

                // Update UI elements
                centerPlayButton.Visibility = Visibility.Collapsed; // Hide when playing
                dropZone.Visibility = Visibility.Collapsed;
                UpdatePlayPauseIcon();
                ShowControlBar(); // Show controls when media loads
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error loading media: {ex.Message}", "Error",
                    MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private WindowState previousWindowState = WindowState.Normal;
        private System.Windows.Rect previousWindowRect = new System.Windows.Rect();

        private void ToggleFullscreen()
        {
            if (!isFullscreen)
            {
                // Store current window state and position before going fullscreen
                previousWindowState = WindowState;
                previousWindowRect = new Rect(this.Left, this.Top, this.Width, this.Height);

                // Enter true fullscreen - hide all Windows UI elements
                WindowStyle = WindowStyle.None;
                WindowState = WindowState.Maximized;
                ResizeMode = ResizeMode.NoResize; // Prevent resizing in fullscreen
                Topmost = true;
                isFullscreen = true;

                // Hide the menu bar in fullscreen
                foreach (var child in ((Grid)Content).Children)
                {
                    if (child is Menu)
                    {
                        ((Menu)child).Visibility = Visibility.Collapsed;
                        break;
                    }
                }
            }
            else
            {
                // Exit fullscreen - restore previous window state
                WindowStyle = WindowStyle.SingleBorderWindow;
                ResizeMode = ResizeMode.CanResize; // Allow resizing again

                // Restore previous window dimensions and state
                if (previousWindowState == WindowState.Maximized)
                {
                    WindowState = WindowState.Maximized;
                }
                else
                {
                    WindowState = WindowState.Normal;
                    this.Left = previousWindowRect.Left;
                    this.Top = previousWindowRect.Top;
                    this.Width = previousWindowRect.Width;
                    this.Height = previousWindowRect.Height;
                }

                Topmost = false;
                isFullscreen = false;

                // Show the menu bar again
                foreach (var child in ((Grid)Content).Children)
                {
                    if (child is Menu)
                    {
                        ((Menu)child).Visibility = Visibility.Visible;
                        break;
                    }
                }
            }
        }

        // Methods to update icons
        private void UpdatePlayPauseIcon()
        {
            // Update center play button icon
            var centerPath = centerPlayButton.Content as ShapePath;
            if (centerPath != null)
            {
                centerPath.Data = (Geometry)this.FindResource(isPlaying ? "PauseIcon" : "PlayIcon");
            }

            // Update play/pause button icon in control bar
            var playPausePath = playPauseButton.Content as ShapePath;
            if (playPausePath != null)
            {
                playPausePath.Data = (Geometry)this.FindResource(isPlaying ? "PauseIcon" : "PlayIcon");
            }
        }

        private void UpdateVolumeIcon()
        {
            // The volume button is not defined in XAML, so we'll skip this for now
            // In the XAML, there's only a volumeSlider but no associated volume button icon to update
        }

        // Method to show control bar temporarily
        private async void ShowControlBar()
        {
            // Ensure control bar is visible and opaque
            controlBar.Opacity = 1;

            // If in fullscreen mode, schedule hiding after a delay
            if (isFullscreen)
            {
                // Cancel any previous scheduled hiding
                if (_hideControlsTask != null && !_hideControlsTask.IsCompleted)
                {
                    // We can't cancel the task, but we'll reset the opacity when it runs
                }

                _hideControlsTask = System.Threading.Tasks.Task.Delay(3000);
                await _hideControlsTask;

                // Only hide if still in fullscreen and mouse is not over controls
                if (isFullscreen && !controlBar.IsMouseOver)
                {
                    controlBar.Opacity = 0.3; // Semi-transparent in fullscreen
                }
            }
        }

        private System.Threading.Tasks.Task? _hideControlsTask;

        // Timer to update current time and timeline slider
        private void UIUpdateTimer_Tick(object? sender, EventArgs e)
        {
            if (mediaElement.Source != null && mediaElement.NaturalDuration.HasTimeSpan)
            {
                // Update timeline slider if it's not being dragged
                if (!isDraggingSlider)
                {
                    timelineSlider.Value = mediaElement.Position.TotalSeconds;
                }

                // Update center play button visibility based on actual playback state
                // Check if media is actually playing by looking at the playback state
                // We'll determine this by seeing if the position is advancing over time
                bool isActuallyPlaying = false;

                double currentPosition = mediaElement.Position.TotalSeconds;
                TimeSpan timeSinceLastCheck = DateTime.Now - previousCheckTime;

                // If we have a previous position and time, check if position advanced appropriately
                if (previousCheckTime != DateTime.MinValue && timeSinceLastCheck.TotalSeconds > 0)
                {
                    double expectedAdvance = timeSinceLastCheck.TotalSeconds; // Assuming normal speed
                    double actualAdvance = currentPosition - previousPosition;

                    // If position advanced by roughly the elapsed time, media is playing
                    isActuallyPlaying = Math.Abs(actualAdvance - expectedAdvance) < 0.5 && actualAdvance > 0;
                }

                // Also check if position is within bounds and advancing
                if (mediaElement.NaturalDuration.HasTimeSpan &&
                    mediaElement.Position < mediaElement.NaturalDuration.TimeSpan &&
                    mediaElement.Position.TotalSeconds > 0 && !isActuallyPlaying)
                {
                    // If position is advancing but not by expected amount, still consider playing
                    if (currentPosition > previousPosition && previousPosition >= 0)
                    {
                        isActuallyPlaying = true;
                    }
                }

                // Update stored values for next comparison
                previousPosition = currentPosition;
                previousCheckTime = DateTime.Now;

                System.Console.WriteLine($"UIUpdateTimer_Tick: isActuallyPlaying={isActuallyPlaying}, isPlaying={isPlaying}, isDraggingSlider={isDraggingSlider}");

                // Check if enough time has passed since the last user action
                bool isWithinUserActionCooldown = (DateTime.Now - lastUserActionTime).TotalMilliseconds < USER_ACTION_COOLDOWN_MS;

                // Only update the isPlaying flag if it differs from actual state AND we're not in user action cooldown
                // This prevents the timer from overriding user's play/pause decisions
                if (isActuallyPlaying != isPlaying && !isDraggingSlider && !isWithinUserActionCooldown)
                {
                    isPlaying = isActuallyPlaying;
                    System.Console.WriteLine($"UIUpdateTimer updated isPlaying to {isPlaying}");
                    UpdatePlayPauseIcon();
                }

                // Update UI based on actual state
                if (isActuallyPlaying)
                {
                    centerPlayButton.Visibility = Visibility.Collapsed;
                    System.Console.WriteLine("UIUpdateTimer set centerPlayButton to Collapsed");
                }
                else
                {
                    centerPlayButton.Visibility = Visibility.Visible;
                    System.Console.WriteLine("UIUpdateTimer set centerPlayButton to Visible");
                }

                // Update the progress indicator width based on current position
                if (mediaElement.NaturalDuration.HasTimeSpan && !isDraggingSlider)
                {
                    double progressPercentage = mediaElement.Position.TotalSeconds / mediaElement.NaturalDuration.TimeSpan.TotalSeconds;
                    System.Console.WriteLine($"Progress calculation: Position={mediaElement.Position.TotalSeconds}, Duration={mediaElement.NaturalDuration.TimeSpan.TotalSeconds}, Percentage={progressPercentage}");

                    if (progressPercentage >= 0 && progressPercentage <= 1)
                    {
                        System.Console.WriteLine($"Calling UpdateSliderProgressIndicator with percentage: {progressPercentage}");
                        UpdateSliderProgressIndicator(progressPercentage);
                    }
                    else
                    {
                        System.Console.WriteLine($"Progress percentage out of range: {progressPercentage}");
                    }
                }
                else
                {
                    System.Console.WriteLine("Media element has no natural duration or is being dragged");
                }
            }
        }

        private void UpdateSliderProgressIndicator(double progressPercentage)
        {
            System.Console.WriteLine($"UpdateSliderProgressIndicator called with progressPercentage: {progressPercentage}");
            // Update the progress indicator width based on the progress percentage
            if (timelineSlider != null)
            {
                System.Console.WriteLine($"Timeline slider actual width: {timelineSlider.ActualWidth}");
                // Get the width of the slider track
                double trackWidth = timelineSlider.ActualWidth - 10; // Account for margin
                System.Console.WriteLine($"Calculated trackWidth: {trackWidth}");

                if (trackWidth > 0)
                {
                    // Update the progress indicator width
                    // We need to access the template part directly
                    var templateChild = FindVisualChild<System.Windows.Shapes.Rectangle>(timelineSlider, "ProgressIndicator");
                    if (templateChild != null)
                    {
                        double newWidth = trackWidth * progressPercentage;
                        templateChild.Width = newWidth;
                        System.Console.WriteLine($"Updated progress indicator width to: {newWidth}");
                    }
                    else
                    {
                        System.Console.WriteLine("Could not find ProgressIndicator rectangle in slider template");
                    }
                }
            }
        }

        // Helper method to find child elements in a control template
        private childItem? FindVisualChild<childItem>(DependencyObject? obj, string childName) where childItem : FrameworkElement
        {
            if (obj == null) return null;

            for (int i = 0; i < VisualTreeHelper.GetChildrenCount(obj); i++)
            {
                DependencyObject? child = VisualTreeHelper.GetChild(obj, i);
                if (child != null && child is childItem childOfT && childOfT.Name == childName)
                {
                    return childOfT;
                }
                else
                {
                    var childOfChild = FindVisualChild<childItem>(child, childName);
                    if (childOfChild != null)
                        return childOfChild;
                }
            }
            return null;
        }

        protected override void OnMouseEnter(MouseEventArgs e)
        {
            base.OnMouseEnter(e);
            // Show control bar immediately on mouse enter anywhere in the window
            ShowControlBar();
        }

        protected override void OnMouseLeave(MouseEventArgs e)
        {
            base.OnMouseLeave(e);
            if (isFullscreen && !controlBar.IsMouseOver)
            {
                // In fullscreen mode, hide controls after a delay when mouse leaves
                System.Threading.Tasks.Task.Delay(2000).ContinueWith(_ =>
                {
                    if (isFullscreen && !controlBar.IsMouseOver && !mediaElement.IsMouseOver)
                    {
                        this.Dispatcher.BeginInvoke(new Action(() =>
                        {
                            controlBar.Opacity = 0.3;
                        }));
                    }
                });
            }
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            // Show control bar immediately on mouse movement
            ShowControlBar();
        }

        protected override void OnClosed(EventArgs e)
        {
            uiUpdateTimer?.Stop();
            base.OnClosed(e);
        }
    }

    // Simple dialog for URL input
    public partial class UrlInputDialog : Window
    {
        public string? Url { get; private set; }

        public UrlInputDialog()
        {
            Title = "Enter Media URL";
            Width = 400;
            Height = 150;
            WindowStartupLocation = WindowStartupLocation.CenterOwner;

            StackPanel panel = new StackPanel { Margin = new Thickness(10) };

            Label label = new Label { Content = "Enter media URL:", Margin = new Thickness(0, 0, 0, 10) };

            TextBox textBox = new TextBox
            {
                Name = "urlTextBox",
                Margin = new Thickness(0, 0, 0, 10),
                Text = "http://"
            };

            StackPanel buttonPanel = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };

            Button okButton = new Button { Content = "OK", Width = 80, Margin = new Thickness(0, 0, 10, 0) };
            okButton.Click += (s, e) => { Url = textBox.Text; DialogResult = true; };

            Button cancelButton = new Button { Content = "Cancel", Width = 80 };
            cancelButton.Click += (s, e) => { DialogResult = false; };

            buttonPanel.Children.Add(okButton);
            buttonPanel.Children.Add(cancelButton);

            panel.Children.Add(label);
            panel.Children.Add(textBox);
            panel.Children.Add(buttonPanel);

            Content = panel;
        }
    }
}

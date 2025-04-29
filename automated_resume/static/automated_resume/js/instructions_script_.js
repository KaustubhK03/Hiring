document.addEventListener('DOMContentLoaded', () => {
    let fullscreenExitCount = 0;
    // Esc Modal with its continueQuiz Button
    const modal = document.querySelector('.modal-overlay');
    const continueQuizBtn = document.querySelector('.close-modal-btn');

    // Tab Swicth Modal with its continueQuiz Button
    const tabswitchModal = document.querySelector(".modal-overlay-four")
    const tabswitchModalBtn = document.querySelector(".close-modal-btn-tab")

    // UnansweredQuestions Modal with its quiz button
    const unansweredModal = document.querySelector('.modal-overlay-two')
    const continueUnanswered = document.querySelector('.close-modal-btn-two')

    // Violation Modal
    const continueViolation = document.querySelector('.modal-overlay-three')
    const continueViolationBtn = document.querySelector('.close-modal-btn-violation')

    const unansweredSubmitBtn = document.querySelector('.submit-button-class')
    const timerElement = document.getElementById('timer');
    const quizForm = document.getElementById('quizForm');
    const questions = document.querySelectorAll('.question');
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const questionNavButtons = document.querySelectorAll('.question-nav button');
    const videoElement = document.getElementById('video');
    const startQuizButton = document.getElementById('startQuizButton');
    const navbar = document.querySelector("nav.navbar");
    const headerText = document.getElementById('instructions-header')
    const instructionsContainer = document.querySelector(".instructions");
    const quizContainer = document.getElementById("quiz-container");
    let countdown; // Variable to store countdown interval
    let countdownActive = false; // Track if countdown is active
    let currentQuestionIndex = 0;
    let num_of_violations = 0;
    let flags = 0;
    let tabswitchCount = 0;
    let timerInterval;
    let selectedAnswers = {};
    let mediaRecorder;
    let recordedChunks = [];
    let stream;
    let socket;
    const username = document.getElementById("user-info")?.getAttribute("data-username") || "anonymous";

    function startWebcam() {
        /**
         * Initializes the webcam and microphone, sets up the WebSocket for proctoring,
         * and starts audio recording and video streaming for real-time exam monitoring.
         * 
         * Key functionalities:
         * - Requests user permission to access webcam and microphone.
         * - Sets up MediaRecorder to record audio data.
         * - Establishes a WebSocket connection with the backend to send video frames.
         * - Starts quiz UI, fullscreen mode, and countdown timer upon successful connection.
         * - Handles cheating detection and violation threshold messages from the server.
         * 
         * Called when the quiz starts to initiate all required proctoring functionalities.
         */
        navigator.mediaDevices.getUserMedia({ video: true, audio: true })
            .then(function(localStream) {
                stream = localStream;
                videoElement.srcObject = stream;

                // Start recording audio separately
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = event => {
                    if (event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };
                mediaRecorder.onstop = saveRecording;
                mediaRecorder.start();

                // Send frames to WebSocket
                socket = new WebSocket('ws://localhost:8000/ws/proctoring');
                socket.onopen = function () {
                    console.log("WebSocket connected, sending video frames.");
                    startQuizButton.disabled = false;
                    modal.classList.add('hide');
                    document.querySelector('.actions').style.display = 'none';
                    document.querySelector('.instructions').style.display = 'none';
                    document.getElementById('quiz-container').style.display = 'block';
                    requestFullScreen(document.documentElement);
                    startTimer();
                    startStreaming(socket);
                };
                socket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.message === "Cheating detected! Submitting the quiz...") {
                        clearInterval(timerInterval);
                        saveSelectedAnswer();
                        stopRecordingAndSubmitQuiz();
                        sendFlagsToServer(flags);
                        const answersInput = document.createElement('input');
                        answersInput.type = 'hidden';
                        answersInput.name = 'selectedAnswers';
                        answersInput.value = JSON.stringify(selectedAnswers);
                        quizForm.appendChild(answersInput);
                        quizForm.submit();  // Automatically submit the quiz
                    }
                    if (data.message === "Violation Threshold crossed") {
                        if (num_of_violations < 1){
                            num_of_violations += 1
                            continueViolation.classList.remove("hide");
                            flags += 1;
                            setTimeout(() => {
                                autoClickButton(continueViolationBtn, "Continue Quiz");
                            }, 1000);
                            document.body.style.pointerEvents = 'auto';
                        }
                        else {
                            saveEverythingAndSubmit();
                        }
                    }
                };
            })
            .catch(function(err) {
                console.error("Error accessing webcam: ", err);
            });
    }
    // Logic to continue quiz when violations are detected. This is only called when a violation threshold is crossed
    // and only once as if the violation threshold is crossed more than once, it will call saveEverythingAndSubmit()
    function Violation_continued() {
        continueViolation.classList.add('hide');
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ "action": "resume" }));
            console.log("Sent resume action to WebSocket");
        } else {
            console.error("WebSocket is not open. Cannot send resume action.");
        }
        document.body.style.pointerEvents = 'auto';
    }
    // Logic to give frames to consumers.py in order to make a video
    function startStreaming(socket) {
        let canvas = document.createElement('canvas');
        let ctx = canvas.getContext('2d');
        let video = document.getElementById('video');

        setInterval(() => {
            if (video.readyState === 4) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

                // Convert frame to base64
                let frameData = canvas.toDataURL('image/jpeg');
                socket.send(JSON.stringify({ frame: frameData }));
            }
        }, 100);  // Adjust interval based on performance
    }

    // Start quiz and initialize webcam and UI
    startQuizButton.addEventListener("click", function () {
        // Hide the navbar
        navbar.style.display = "none";
        startWebcam();
        headerText.style.display = "none"; // Hide header text
        // Hide the instructions and show the quiz container
        if (instructionsContainer) {
            instructionsContainer.style.display = "none";
        }
        if (quizContainer) {
            quizContainer.style.display = "block";
        }
    });

    // Save the webcam recording to backend
    function saveRecording() {
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        const filename = `${username}_recording_${new Date().toISOString().replace(/:/g, "-")}.webm`;
        // Send recorded video to backend
        const formData = new FormData();
        formData.append('video', blob, filename);

        fetch('/save-recording/', {  
            method: 'POST',
            body: formData
        }).then(response => response.json())
        .then(data => console.log('Recording saved:', data))
        .catch(error => console.error('Error saving recording:', error));
    }


    // Stop video/audio recording and submit quiz data
    function stopRecordingAndSubmitQuiz() {
        mediaRecorder.onstop = function () {
            saveRecording();  // Save the recording before submitting

            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = function () {
                const base64Audio = reader.result.split(',')[1];
                socket.send(JSON.stringify({ audio: base64Audio }));
            };
        };
        mediaRecorder.stop();
    }

    // Request full screen for the given element
    const requestFullScreen = (element) => {
        if (element.requestFullscreen) {
            element.requestFullscreen();
        } else if (element.mozRequestFullScreen) {
            element.mozRequestFullScreen();
        } else if (element.webkitRequestFullscreen) {
            element.webkitRequestFullscreen();
        } else if (element.msRequestFullscreen) {
            element.msRequestFullscreen();
        }
    };
    
    // Handle tab switching logic
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState == "visible") {
          console.log("tab is active");
        } else {
            if (tabswitchCount < 1){
                tabswitchCount += 1;
                tabswitchModal.classList.remove('hide');
                setTimeout(() => {
                    autoClickButton(tabswitchModalBtn, "Continue Quiz");
                }, 1000);
                flags += 1;
            }
            else {
                saveEverythingAndSubmit();
            }
        }
    });

    // Hide the tab switch modal
    const tabswitchFunction = () => {
        tabswitchModal.classList.add('hide')
    }

    // Check if fullscreen mode is active
    const isFullScreenActive = () => {
        return document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement;
    };

    // Handle when user exits fullscreen
    const onFullScreenChange = () => {
        if (!isFullScreenActive()) {
            fullscreenExitCount++;
            if (fullscreenExitCount === 1) {
                modal.classList.remove('hide');
                startCountdown();
                flags += 1;
            } else if (fullscreenExitCount >= 2) {
                saveEverythingAndSubmit();
            }
        }
    };

    // Starts a 10-second countdown on modal
    const startCountdown = () => {
        let timeLeft = 10; // Start from 10 seconds
        const continueButton = document.querySelector(".close-modal-btn");
        // Ensure any existing countdown is cleared before starting a new one
        if (countdownActive) {
            clearInterval(countdown);
        }
        countdownActive = true;
        // Display initial time
        continueButton.textContent = `Continue Quiz (${timeLeft}s)`;

        // Start the countdown
        countdown = setInterval(() => {
            timeLeft--;
            continueButton.textContent = `Continue Quiz (${timeLeft}s)`;

            if (timeLeft <= 0) {
                clearInterval(countdown); // Stop the timer
                countdownActive = false; // Reset Flag
                saveEverythingAndSubmit(); // Auto-submit the quiz
            }
        }, 1000);
    };
    // Close modal and return to fullscreen mode
    const closeModal = () => {
        modal.classList.add('hide');
        document.body.style.pointerEvents = 'auto';
        requestFullScreen(document.documentElement);
    };

    // When the user presses continue quiz button to resume quiz
    const ContinueQuiz = () => {
        unansweredModal.classList.add('hide');
        document.body.style.pointerEvents = 'auto';
    };

    // auto click on continue quiz button when the user doesn't
    function autoClickButton(button, initialText) {
        let timeLeft = 10;
        button.textContent = `${initialText} (${timeLeft}s)`;

        const timerInterval = setInterval(() => {
            timeLeft--;
            button.textContent = `${initialText} (${timeLeft}s)`;
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                button.click();
            }
        }, 1000);
    }
    // logic to update nav button styles
    const updateNavigationButtonStyles = () => {
        questions.forEach((question, index) => {
            const button = questionNavButtons[index];
            const selectedOption = question.querySelector('input[type="radio"]:checked');
            const touched_option = question.querySelector('input[type="radio"]:checked')
            // Reset button classes
            button.classList.remove('unvisited', 'visited-unanswered', 'answered');

            if (selectedOption) {
                button.classList.add('answered'); // Green when answered
                button.style.backgroundColor = '#66ff66';
            } else {
                button.classList.add('unvisited'); // Grey when unvisited
                button.style.backgroundColor = '#FFFF00';
            }
        });
    };

    // Attach event listeners to update colors when selecting an answer
    questions.forEach((question, index) => {
        const options = question.querySelectorAll('input[type="radio"]');
        options.forEach(option => {
            option.addEventListener('change', () => {
                saveSelectedAnswer();
                updateNavigationButtonStyles(); // Ensure nav button color updates
            });
        });
    });
    // Start the quiz countdown timer
    const startTimer = () => {
        let timeRemaining = quizTimeLimit * 60;
        const updateTimer = () => {
            const minutes = Math.floor(timeRemaining / 60);
            const seconds = timeRemaining % 60;
            timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

            if (timeRemaining <= 0) {
                saveEverythingAndSubmit();
            }

            timeRemaining--;
        };

        timerInterval = setInterval(updateTimer, 1000);
        updateTimer();
    };

    // Store selected answers from UI
    const saveSelectedAnswer = () => {
        const tempAnswers = {};
        questions.forEach((question, index) => {
            const questionNumber = `q${index + 1}`;
            const selectedOption = question.querySelector('input[type="radio"]:checked');

            if (selectedOption) {
                tempAnswers[questionNumber] = selectedOption.getAttribute('data-value');
            } else {
                tempAnswers[questionNumber] = "Not Answered";
            }
        });

        const sortedKeys = Object.keys(tempAnswers).sort((a, b) => {
            return parseInt(a.substring(1)) - parseInt(b.substring(1));
        });

        selectedAnswers = {};
        sortedKeys.forEach(key => {
            selectedAnswers[key] = tempAnswers[key];
        });
    };

    // Update visibility and styling of current question
    const updateQuestionVisibility = () => {
        questions.forEach((question, index) => {
            question.classList.toggle('active', index === currentQuestionIndex);
            question.style.borderColor = index === currentQuestionIndex ? '#808080' : '#ccc';
            question.style.backgroundColor = index === currentQuestionIndex ? '#808080' : '#f9f9f9';
            const questionButton = questionNavButtons[index];

            // If the question has been visited but not answered, make the button red
            if (question.classList.contains('visited') && !question.querySelector('input:checked')) {
                questionButton.style.backgroundColor = '#ff4d4d'; // Red for unanswerable but visited
            }
            // If the question is answered, turn the button green
            else if (question.querySelector('input:checked')) {
                questionButton.style.backgroundColor = '#66ff66'; // Green for answered
            }
            // Otherwise, keep the button blue for unvisited questions
            else {
                questionButton.style.backgroundColor = '#808080'; // Blue for unvisited
            }
        });
    };

    // Question navigation buttons (Prev, Next, Direct Jump)
    prevButton.addEventListener('click', () => {
        if (currentQuestionIndex > 0) {
            saveSelectedAnswer();
            currentQuestionIndex--;
            updateQuestionVisibility();
            updateNavigationButtonStyles();
        }
    });

    nextButton.addEventListener('click', () => {
        if (currentQuestionIndex < questions.length - 1) {
            saveSelectedAnswer();
            currentQuestionIndex++;
            updateQuestionVisibility();
            updateNavigationButtonStyles();
        }
    });

    questionNavButtons.forEach(button => {
        button.addEventListener('click', () => {
            const target = parseInt(button.getAttribute('data-target'), 10) - 1;
            saveSelectedAnswer();
            currentQuestionIndex = target;
            updateQuestionVisibility();
            updateNavigationButtonStyles();
        });
    });

    // Highlight unanswered questions as visited on timeout
    const markAllUnansweredAsVisited = () => {
        questions.forEach((question, index) => {
            const button = questionNavButtons[index];
            const selectedOption = question.querySelector('input[type="radio"]:checked');

            if (!selectedOption) {
                button.classList.remove('unvisited', 'answered');
                button.classList.add('visited-unanswered');
            }
        });
    };

    timerElement.addEventListener('timer-expired', markAllUnansweredAsVisited);

    // Submit quiz and store answers in a hidden input
    quizForm.addEventListener('submit', (e) => {
        saveSelectedAnswer();
        updateNavigationButtonStyles();
        const existingInput = document.querySelector('input[name="selectedAnswers"]');
        if (existingInput) {
            existingInput.remove();
        }

        const unansweredQuestions = Object.values(selectedAnswers).filter(answer => answer === "Not Answered").length;
        const answersInput = document.createElement('input');
        answersInput.type = 'hidden';
        answersInput.name = 'selectedAnswers';
        answersInput.value = JSON.stringify(selectedAnswers);
        quizForm.appendChild(answersInput);
        if (unansweredQuestions > 0) {
            e.preventDefault();
            unansweredModal.classList.remove('hide');
        }
    });

    // Send the count of violations (flags) to the backend
    function sendFlagsToServer(flags) {
        fetch("save_flags/", {  // Django URL
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken() // Ensure CSRF protection
            },
            body: JSON.stringify({ flags: flags })  // Send flags as JSON
        })
        .then(response => response.json())
        .then(data => console.log("Flags sent successfully:", data))
        .catch(error => console.error("Error sending flags:", error));
    }
    
    // Helper function to get CSRF token from cookies
    function getCSRFToken() {
        let cookieValue = null;
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith("csrftoken=")) {
                cookieValue = cookie.substring("csrftoken=".length, cookie.length);
                break;
            }
        }
        return cookieValue;
    }

    // Final submit logic that stops everything and submits form
    function saveEverythingAndSubmit() {
        clearInterval(timerInterval);
        saveSelectedAnswer();
        stopRecordingAndSubmitQuiz();
        sendFlagsToServer(flags);
        const answersInput = document.createElement('input');
        answersInput.type = 'hidden';
        answersInput.name = 'selectedAnswers';
        answersInput.value = JSON.stringify(selectedAnswers);
        quizForm.appendChild(answersInput);
        quizForm.submit();  // Automatically submit the quiz
    }
    // Listen for fullscreen changes
    document.addEventListener('fullscreenchange', onFullScreenChange);
    document.addEventListener('mozfullscreenchange', onFullScreenChange);
    document.addEventListener('webkitfullscreenchange', onFullScreenChange);
    document.addEventListener('msfullscreenchange', onFullScreenChange);

    // Event listeners for modal buttons
    continueQuizBtn.addEventListener('click', () => {
        clearInterval(countdown); // Stop countdown
        countdownActive = false; // Reset flag
        closeModal();
    }); //
    continueUnanswered.addEventListener('click', ContinueQuiz);
    unansweredSubmitBtn.addEventListener('click', saveEverythingAndSubmit);
    continueViolationBtn.addEventListener('click', Violation_continued);
    tabswitchModalBtn.addEventListener('click', tabswitchFunction); //
});
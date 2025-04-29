document.addEventListener("DOMContentLoaded", function () {
    const runBtn = document.getElementById("runBtn");
    const runAllBtn = document.getElementById("executeTestCases");
    const editor = document.querySelector(".code-editor");

    let currentQuestionIndex = 0;
    let userCode = {}; // { questionId: "user's code" }
    const questions = JSON.parse(document.getElementById("question-data-list").text);
    // Access Modal elements here
    // Start Test Modal elements here
    const startTestModal = document.getElementById("startTestModal");
    const startTestBtn = document.getElementById("startTestBtn");

    // Violation Modal elements here
    const violationModal = document.getElementById("violationModal");
    const closeViolationBtn = document.getElementById("closeViolationBtn");

    // Tab Switch Modal elements here
    const tabSwitchModal = document.getElementById("tabSwitchModal");
    const tabViolationBtn = document.getElementById("tabViolationBtn");

    // Full Screen Violation Modal elements here
    const fullScreenSwitchModal = document.getElementById("fullScreenSwitchModal");
    const fullScreenViolationBtn = document.getElementById("fullScreenViolationBtn");

    // Are you sure you want to submit Modal
    const submitTestModal = document.getElementById("submitTestModal");
    const closeSubmitBtn = document.getElementById("closeSubmitBtn");
    const submitTestBtn = document.getElementById("submitTestBtn");

    // are you sure you want to clear the stub?
    const clearStdinModal = document.getElementById("clearStdinModal");
    const dontclearStdin = document.getElementById("dontclearStdin");
    const clearStdin = document.getElementById("clearStdin");

    // Submit btn
    const submitBtn = document.querySelector(".submit-button");

    // clear stdin btn
    const mainClearStdinBtn = document.getElementById("mainClearStdinBtn");
    // timer element
    const codingtimerElement = document.getElementById("timer-element")
    let submissionData = {};  // Global object to store each question's data
    const languageDropdown = document.getElementById("languageName");
    const publicCases = document.getElementById("publicCases");
    let countdownActive = false;
    let socket;
    let fullscreenExitCount = 0;
    let recordedChunks = [];
    let num_of_violations = 0;
    let flags = 0;
    let tabswitchCount = 0;

    const username = document.getElementById("user-info")?.getAttribute("data-username") || "anonymous";

    function renderQuestion(index) {
        const question = questions[index];
        currentQuestionIndex = index;
        console.log("Rendering question", questions);
        console.log("Rendering question", question);
        // Load question details
        $(".problem-title").text(question.Problem_Name);
        $(".problem-statement").html(`<strong>Problem Statement:</strong> ${question.Problem_Statement}`);
        $(".question-content .mt-2 p").text(question.Description);
        $(".sample-cases").html(
            question.Public_Test_Cases.map(tc => `
                <p class="sample-case">Sample Input: ${tc.Input}<br/>Sample Output: ${tc.Expected_Output}</p>
            `).join("")
        );
    
        // Load code from memory or starter
        const savedCode = userCode[question.id] || question.starter_code || "";
        $("#codeEditor").val(savedCode);
    
        // Load test case status placeholders
        const testListHTML = question.Public_Test_Cases.map((_, i) =>
            `<div id="PublicTestCase${i}" class="test-case">Test Case ${i + 1}</div>`
        ).join("") +
        question.Private_Test_Cases.map((_, i) =>
            `<div id="PrivateTestCase${i}" class="test-case">Private Test Case ${i + 1}</div>`
        ).join("");
        $(".test-items").html(testListHTML);
    }

    $(".next-button").click(() => {
        saveCurrentCode();
        console.log("Saved Codes: ", userCode);
        if (currentQuestionIndex < questions.length - 1) {
            renderQuestion(currentQuestionIndex + 1);
        }
    });
    
    $(".prev-button").click(() => {
        saveCurrentCode();
        if (currentQuestionIndex > 0) {
            renderQuestion(currentQuestionIndex - 1);
        }
    });
    
    function saveCurrentCode() {
        const qid = questions[currentQuestionIndex].id;
        userCode[qid] = $("#codeEditor").val();
    }

    // StartTest Modal Eventlistner
    // Function to start full-screen mode
    function requestFullScreen() {
        let docElem = document.documentElement;
        if (docElem.requestFullscreen) {
            docElem.requestFullscreen();
        } else if (docElem.mozRequestFullScreen) {
            docElem.mozRequestFullScreen();
        } else if (docElem.webkitRequestFullscreen) {
            docElem.webkitRequestFullscreen();
        } else if (docElem.msRequestFullscreen) {
            docElem.msRequestFullscreen();
        }
    }

    // Function to start the WebSocket connection
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
                // videoElement.srcObject = stream;
                // Dynamically create a hidden video element (not attached to DOM)
                video = document.createElement('video');
                video.srcObject = stream;
                video.muted = true;
                video.play();

                // Create an off-DOM canvas element
                canvas = document.createElement('canvas');
                ctx = canvas.getContext('2d');

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
                    
                    requestFullScreen(document.documentElement);
                    startTimer();
                    startStreaming(socket);
                };
                socket.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.message === "Cheating detected! Submitting the quiz...") {
                        // clearInterval(timerInterval);
                        // stopRecordingAndSubmitQuiz();
                        // sendFlagsToServer(flags);
                        submitCode();
                    }
                    if (data.message === "Violation Threshold crossed") {
                        if (num_of_violations < 1){
                            num_of_violations += 1
                            violationModal.classList.remove("hidden");
                            flags += 1;
                            setTimeout(() => {
                                autoClickButton(closeViolationBtn, "Continue Quiz");
                            }, 1000);
                            document.body.style.pointerEvents = 'auto';
                        }
                        else {
                            submitCode();
                        }
                    }
                };
            })
            .catch(function(err) {
                console.error("Error accessing webcam: ", err);
            });
    }

    function saveRecording() {
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        const filename = `${username}_coding_recording_${new Date().toISOString().replace(/:/g, "-")}.webm`;
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

    function startStreaming(socket) {
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

    // Handle Tab Switch Logic
    // Handle tab switching logic
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState == "visible") {
          console.log("tab is active");
        } else {
            if (tabswitchCount < 1){
                tabswitchCount += 1;
                tabSwitchModal.classList.remove('hidden');
                setTimeout(() => {
                    autoClickButton(tabViolationBtn, "Continue Quiz");
                }, 1000);
                flags += 1;
            }
            else {
                submitCode();
            }
        }
    });

    // Hide the tab switch modal
    const tabswitchFunction = () => {
        tabSwitchModal.classList.add('hidden')
    }

    // handle full-screen logic
    // Check if fullscreen mode is active
    const isFullScreenActive = () => {
        return document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement;
    };

    // Handle when user exits fullscreen
    const onFullScreenChange = () => {
        if (!isFullScreenActive()) {
            fullscreenExitCount++;
            if (fullscreenExitCount === 1) {
                fullScreenSwitchModal.classList.remove('hidden');
                startCountdown();
                flags += 1;
            } else if (fullscreenExitCount >= 2) {
                submitCode();
            }
        }
    };

    // Start Timer Logic
    function startTimer() {
        console.log("Coding Time Limit (raw): ", coding_time_limit);
    
        // coding_time_limit will be a string like "1:00:00" to change it to datetime we need to:
        const [hours, minutes, seconds] = coding_time_limit.split(":").map(Number);
        let timeRemaining = hours * 3600 + minutes * 60 + seconds;
    
        console.log("Total seconds:", timeRemaining);
    
        const updateTimer = () => {
            const minutes = Math.floor(timeRemaining / 60);
            const seconds = timeRemaining % 60;
            codingtimerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    
            if (timeRemaining <= 0) {
                submitCode();
                clearInterval(timerInterval);
            }
    
            timeRemaining--;
        };
    
        timerInterval = setInterval(updateTimer, 1000);
        updateTimer();
    }

    // Starts a 10-second countdown on modal
    const startCountdown = () => {
        let timeLeft = 10; // Start from 10 seconds
        const continueButton = document.querySelector(".close-modal-btn-fullscreen");
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
                submitCode(); // Auto-submit the quiz
            }
        }, 1000);
    };

    function Violation_continued() {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ "action": "resume" }));
            console.log("Sent resume action to WebSocket");
        } else {
            console.error("WebSocket is not open. Cannot send resume action.");
        }
        document.body.style.pointerEvents = 'auto';
    }
    function give_code_to_backend() {

        $.ajax({

            url: "get_code_from_frontend/",

            method: "POST",
            
            contentType: "application/json",  // Important for JSON
            
            data: JSON.stringify({
                source_code: $("#codeEditor").val(),
                language_id: $("#languageName").val(),
                stdin: $("#stdin").val()
            }),

            success: function(response) {
                let stdout = response.stdout || response.message;
                $("#stdoutBox").text(stdout);
            }
        })
    }

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

    function to_run_test_cases() {
        $.ajax({
            url: "run_test_cases/",

            method: "POST",

            contentType: "application/json",

            data: JSON.stringify({
                source_code: $("#codeEditor").val(),
                language_id: $("#languageName").val(),
                question_id: questions[currentQuestionIndex].id,
            }),
            
            success: function(response) {
                const publicAcceptedList = response.public_accepted_lst;
                const privateAcceptedList = response.private_accepted_lst;
                const totalTestCases = response.total_test_cases;
                const passed_test_cases = response.passed_test_cases;

                const questionId = questions[currentQuestionIndex].id;
                submissionData[questionId] = {
                    source_code: $("#codeEditor").val(),
                    language_id: $("#languageName").val(),
                    total_test_cases: totalTestCases,
                    passed_test_cases: passed_test_cases,
                };

                console.log("Updated Submission Data:", submissionData);

                // Iterate over all test cases
                publicAcceptedList.forEach((status, index) => {
                    const PublictestCaseEl = document.getElementById(`PublicTestCase${index}`);
                    
                    if (!PublictestCaseEl) return;
                    

                    // Clear old classes
                    PublictestCaseEl.classList.remove("text-green-600", "text-red-600");
                    

                    if (status === "Accepted") {
                        PublictestCaseEl.classList.add("text-green-600");
                        PublictestCaseEl.innerHTML += " ✅";
                    } else {
                        PublictestCaseEl.classList.add("text-red-600");
                        PublictestCaseEl.innerHTML += " ❌";
                    }
                });

                // Get inputs and expected outputs for public test cases
                const publicInputs = response.decoded_stdins.slice(0, publicAcceptedList.length);
                const publicExpectedOutputs = response.decoded_expected_outputs.slice(0, publicAcceptedList.length);
                const publicStdouts = response.decoded_stdouts.slice(0, publicAcceptedList.length);

                // Display the output of public test cases
                $("#testCasesStdoutBox").empty();

                // Display detailed info for each public test case
                for (let i = 0; i < publicInputs.length; i++) {
                    const input = publicInputs[i] || "(No Input)";
                    const expected = publicExpectedOutputs[i] || "(No Expected Output)";
                    const actual = publicStdouts[i] || "(No Output)";
                    const status = publicAcceptedList[i] === "Accepted" ? "✅" : "❌";
                    const borderColor = publicAcceptedList[i] === "Accepted" ? "#4CAF50" : "#F44336";

                    $("#testCasesStdoutBox").append(
                        `<div style="margin-bottom: 20px; border: 2px solid ${borderColor}; padding: 15px; border-radius: 10px;">
                            <strong>Test Case ${i + 1} ${status}</strong>
                            <div><strong>Input:</strong><pre style="background-color: #f9f9f9; padding: 8px; border-radius: 4px;">${input}</pre></div>
                            <div><strong>Expected Output:</strong><pre style="background-color: #f9f9f9; padding: 8px; border-radius: 4px;">${expected}</pre></div>
                            <div><strong>Your Output:</strong><pre style="background-color: #f9f9f9; padding: 8px; border-radius: 4px;">${actual}</pre></div>
                        </div>`
                    );
                }

                privateAcceptedList.forEach((status, index) => {
                    const PrivatetestCaseEl = document.getElementById(`PrivateTestCase${index}`);
                    
                    if (!PrivatetestCaseEl) return;
                    

                    // Clear old classes
                    PrivatetestCaseEl.classList.remove("text-green-600", "text-red-600");
                    

                    if (status === "Accepted") {
                        PrivatetestCaseEl.classList.add("text-green-600");
                        PrivatetestCaseEl.innerHTML += " ✅";
                    } else {
                        PrivatetestCaseEl.classList.add("text-red-600");
                        PrivatetestCaseEl.innerHTML += " ❌";
                    }
                });
            }
        })
    }
    function submitCode() {
        $.ajax({
            url: "submit_code/",

            method: "POST",

            contentType: "application/json",

            data: JSON.stringify({
                // source_code: $("#codeEditor").val(),
                // language_id: $("#languageName").val(),
                submissions: submissionData,
                "flags": flags,
            }),
            
            success: function(response) {
                // Diable textarea element
                document.getElementById("executeTestCases").disabled = true;
                sendFlagsToServer();
                stopRecordingAndSubmitQuiz(); // Stop recording and submit the quiz
                
                let message = response.message || "Code submitted successfully!";
                $("#message").text(message);
                if (response.redirect_url) {
                    window.location.href = response.redirect_url;  // Redirect!
                }
            }
        })
    }
    // Send the count of violations (flags) to the backend
    function sendFlagsToServer(flags) {
        fetch("save_flags/", {  // Django URL
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(), // Ensure CSRF protection
                "Test_Name": "Coding"
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

    runBtn.addEventListener("click", function(){
        console.log("Running code...");
        give_code_to_backend();
    })

    runAllBtn.addEventListener("click", function(){
        console.log("Running all test cases...");
        resetTestCases();
        to_run_test_cases();
    })

    startTestBtn.addEventListener("click", () => {
        startWebcam();
        startTestModal.classList.remove("show")
        startTestModal.classList.add("hidden")
    })

    closeViolationBtn.addEventListener("click", () =>{
        violationModal.classList.add("hidden")
        violationModal.classList.remove("show")
        Violation_continued();
    })

    submitBtn.addEventListener("click", function () {
        submitTestModal.classList.remove('hidden');
        submitTestModal.classList.add('show');
    })

    mainClearStdinBtn.addEventListener("click", function () {
        clearStdinModal.classList.remove('hidden');
        clearStdinModal.classList.add('show');
    })

    fullScreenViolationBtn.addEventListener("click", function () {
        fullScreenSwitchModal.classList.add('hidden');
        fullScreenSwitchModal.classList.remove('show');
        document.body.style.pointerEvents = 'auto';
        requestFullScreen(document.documentElement);
    })

    tabViolationBtn.addEventListener("click", tabswitchFunction);

    closeSubmitBtn.addEventListener("click", function () {
        submitTestModal.classList.add("hidden")
        submitTestModal.classList.remove("show")
    })

    submitTestBtn.addEventListener("click", submitCode);

    dontclearStdin.addEventListener("click", function () {
        clearStdinModal.classList.add('hidden');
        clearStdinModal.classList.remove('show');
    });

    clearStdin.addEventListener("click", function () {
        $("#codeEditor").val("");
        clearStdinModal.classList.add('hidden');
        clearStdinModal.classList.remove('show');
    });
    function resetTestCases() {
        const testCases = document.querySelectorAll(".test-case");
        testCases.forEach(tc => {
          tc.classList.remove("text-green-600", "text-red-600", "font-semibold");
          tc.innerHTML = tc.innerHTML.replace(" ✅", "").replace(" ❌", "");
        });
    }

    // Listen for fullscreen changes
    document.addEventListener('fullscreenchange', onFullScreenChange);
    document.addEventListener('mozfullscreenchange', onFullScreenChange);
    document.addEventListener('webkitfullscreenchange', onFullScreenChange);
    document.addEventListener('msfullscreenchange', onFullScreenChange);

    // Jquery to disable copy-paste
    $('body').bind('copy paste',function(e) {
        e.preventDefault(); return false; 
    });    
});
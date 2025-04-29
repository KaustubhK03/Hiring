document.addEventListener("DOMContentLoaded", function () {
    let taskId = getCookie("task_id");

    if (taskId) {
        checkTaskStatus(taskId);
    } else {
        fetchUserProfile(); // Fetch user data from the database if task_id is not found
    }
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        let cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = cookie.substring(name.length + 1);
                break;
            }
        }
    }
    return cookieValue;
}

function checkTaskStatus(taskId) {
    let progressBar = document.getElementById("progress-bar");
    let progressText = document.getElementById("progress-text");

    function updateProgress() {
        fetch(`/progress/${taskId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.status === "PROGRESS") {
                    progressBar.value = data.progress;
                    progressText.innerText = data.description;
                    setTimeout(updateProgress, 1000); // Poll every second
                } else if (data.status === "SUCCESS") {
                    document.getElementById("overlay").style.display = "none";
                    document.getElementById("main-content").classList.remove("blurred");

                    displayUserData(data); // Display fetched ATS data
                    deleteTaskIdCookie();
                } else if (data.status === "FAILURE") {
                    fetchUserProfile();
                }
            })
            .catch(error => {
                console.error("Error:", error);
                deleteTaskIdCookie(); // Ensure cleanup in case of error
            });
    }

    updateProgress();
}

// Function to properly delete the task_id cookie
function deleteTaskIdCookie() {
    document.cookie = "task_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    document.cookie = "task_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/user-profile;";
    document.cookie = "task_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; domain=" + window.location.hostname + "; path=/";
}

// Fetch user profile data if no task_id is found
function fetchUserProfile() {
    /*
    This function should fetch user profile data from the server and 
    display it to the front end.
    **/
    fetch("/user-profile/")
        .then(response => response.json())
        .then(data => {
            document.getElementById("overlay").style.display = "none";
            document.getElementById("main-content").classList.remove("blurred");
            displayUserData(data);
        })
        .catch(error => console.error("Error fetching user profile:", error));
}

function displayUserData(data) {
    // Set ATS Score
    document.getElementById("ats-score").innerText = data.ats_score ? data.ats_score + "%" : "No Score Available";

    // Display Missing Keywords
    let missingKeywordsElement = document.getElementById("missing-keywords");
    missingKeywordsElement.innerHTML = ""; // Clear previous values

    if (Array.isArray(data.missing_keywords) && data.missing_keywords.length > 0) {
        data.missing_keywords.forEach(keyword => {
            let listItem = document.createElement("li");
            listItem.textContent = keyword.trim();
            missingKeywordsElement.appendChild(listItem);
        });
    } else {
        missingKeywordsElement.innerHTML = "<li>No missing keywords</li>";
    }

    // Display ATS Remarks
    let atsRemarksElement = document.getElementById("ats-remarks");
    atsRemarksElement.innerHTML = ""; // Clear previous values

    if (data.ats_remarks) {
        let remarksArray = data.ats_remarks.split(/\. (?=[A-Z])/);
        if (remarksArray) {
            remarksArray.forEach(remark => {
                if (remark.trim() !== "") {
                    let listItem = document.createElement("li");
                    listItem.textContent = remark.trim();
                    atsRemarksElement.appendChild(listItem);
                }
            });
        }
    } else {
        atsRemarksElement.innerHTML = "<li>No remarks available</li>";
    }
}
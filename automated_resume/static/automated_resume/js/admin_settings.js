$(document).ready(function() {
    let saveUrl = $("#adminSettingsForm").data("save-url");
    let deleteUrl = $("#deleteUserForm").data("delete-url");
    $("#adminSettingsForm").submit(function(event) {
        event.preventDefault();
        $.ajax({
            type: "POST",
            url: saveUrl,
            data: $(this).serialize(),
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
            },
            success: function(response) {
                alert("Settings saved successfully!");
            },
            error: function(xhr) {
                alert("Error saving settings.");
            }
        });
    });

    $("#deleteUserForm").submit(function(event) {
        event.preventDefault();
        $.ajax({
            type: "POST",
            url: deleteUrl,
            data: $(this).serialize(),
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
            },
            success: function(response) {
                alert("User data deleted successfully!");
            },
            error: function(xhr) {
                alert("Error deleting user data.");
            }
        });
    });
    function getCSRFToken() {
        return document.cookie.split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
    }
});
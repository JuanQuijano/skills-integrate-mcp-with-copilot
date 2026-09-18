document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("login-form");
  const logoutButton = document.getElementById("logout-button");
  const authStatus = document.getElementById("auth-status");
  const notificationsContainer = document.getElementById(
    "notifications-container"
  );
  const notificationsList = document.getElementById("notifications-list");
  const dashboardContainer = document.getElementById("dashboard-container");
  const dashboardSummary = document.getElementById("dashboard-summary");
  const popularityChart = document.getElementById("popularity-chart");
  const activityMetrics = document.getElementById("activity-metrics");
  let currentUser = null;

  function authHeaders() {
    return currentUser
      ? { Authorization: "Bearer " + currentUser.token }
      : {};
  }

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
  }

  function hideMessage() {
    messageDiv.classList.add("hidden");
  }

  function canViewDashboard() {
    return currentUser && currentUser.role !== "student";
  }

  function updateAuthControls() {
    const isStaff = currentUser?.role === "staff";
    loginForm.classList.toggle("hidden", Boolean(currentUser));
    logoutButton.classList.toggle("hidden", !currentUser);
    signupForm.classList.toggle("hidden", currentUser?.role !== "student");
    notificationsContainer.classList.toggle("hidden", !currentUser);
    dashboardContainer.classList.toggle("hidden", !canViewDashboard());
    authStatus.textContent = currentUser
      ? `Signed in as ${currentUser.email} (${currentUser.role})`
      : "Log in to sign up, review notifications, or coordinate activities.";
    document.querySelectorAll(".delete-btn").forEach((button) => {
      button.classList.toggle("hidden", !isStaff);
    });
  }

  function renderNotifications(notifications) {
    if (!currentUser) {
      notificationsList.innerHTML = "<p>Log in to see notifications.</p>";
      return;
    }

    if (notifications.length === 0) {
      notificationsList.innerHTML = "<p>No notifications yet.</p>";
      return;
    }

    notificationsList.innerHTML = notifications
      .map(
        (notification) => `
          <article class="notification-card">
            <p>${notification.message}</p>
            <small>${new Date(notification.timestamp).toLocaleString()}</small>
          </article>
        `
      )
      .join("");
  }

  function renderDashboard(dashboard) {
    dashboardSummary.innerHTML = `
      <article class="summary-card">
        <strong>${dashboard.overview.total_activities}</strong>
        <span>Activities</span>
      </article>
      <article class="summary-card">
        <strong>${dashboard.overview.total_participants}</strong>
        <span>Total participants</span>
      </article>
      <article class="summary-card">
        <strong>${dashboard.overview.total_seats_remaining}</strong>
        <span>Seats remaining</span>
      </article>
      <article class="summary-card">
        <strong>${dashboard.overview.full_activities}</strong>
        <span>Full activities</span>
      </article>
    `;

    popularityChart.innerHTML = dashboard.popular_activities
      .map(
        (activity) => `
          <div class="chart-row">
            <div class="chart-label">
              <span>${activity.name}</span>
              <span>${activity.participants_count}/${activity.participants_count + activity.seats_remaining}</span>
            </div>
            <div class="chart-bar-track">
              <div class="chart-bar-fill" style="width: ${activity.occupancy_rate}%"></div>
            </div>
          </div>
        `
      )
      .join("");

    activityMetrics.innerHTML = `
      <table class="metrics-table">
        <thead>
          <tr>
            <th>Activity</th>
            <th>Participants</th>
            <th>Seats left</th>
            <th>Trend</th>
          </tr>
        </thead>
        <tbody>
          ${dashboard.activities
            .map((activity) => {
              const trend = activity.history
                .map((entry) => `${entry.participant_count}`)
                .join(" → ");
              return `
                <tr>
                  <td>${activity.name}</td>
                  <td>${activity.participants_count}</td>
                  <td>${activity.seats_remaining}</td>
                  <td>${trend}</td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    `;
  }

  async function fetchNotifications() {
    if (!currentUser) {
      renderNotifications([]);
      return;
    }

    try {
      const response = await fetch("/notifications", {
        headers: authHeaders(),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to load notifications");
      }
      renderNotifications(result.notifications);
    } catch (error) {
      notificationsList.innerHTML = "<p>Unable to load notifications right now.</p>";
      console.error("Error fetching notifications:", error);
    }
  }

  async function fetchDashboard() {
    if (!canViewDashboard()) {
      dashboardSummary.innerHTML = "";
      popularityChart.innerHTML = "";
      activityMetrics.innerHTML = "";
      return;
    }

    try {
      const response = await fetch("/coordinator/dashboard", {
        headers: authHeaders(),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to load dashboard");
      }
      renderDashboard(result);
    } catch (error) {
      dashboardSummary.innerHTML = "<p>Unable to load coordinator dashboard.</p>";
      popularityChart.innerHTML = "";
      activityMetrics.innerHTML = "";
      console.error("Error fetching dashboard:", error);
    }
  }

  async function refreshSignedInViews() {
    await fetchNotifications();
    await fetchDashboard();
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.innerHTML =
        '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
                <h5>Participants:</h5>
                <ul class="participants-list">
                  ${details.participants
                    .map(
                      (email) =>
                        `<li><span class="participant-email">${email}</span><button class="delete-btn" data-activity="${name}" data-email="${email}">❌</button></li>`
                    )
                    .join("")}
                </ul>
              </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${details.seats_remaining} spots left</p>
          <p><strong>Participants:</strong> ${details.participants_count}/${details.max_participants}</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
      updateAuthControls();
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        await fetchActivities();
        await refreshSignedInViews();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }

      setTimeout(hideMessage, 5000);
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        await fetchActivities();
        await refreshSignedInViews();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }

      setTimeout(hideMessage, 5000);
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: document.getElementById("login-email").value,
        password: document.getElementById("login-password").value,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      showMessage(result.detail || "Unable to log in", "error");
      return;
    }
    currentUser = result;
    loginForm.reset();
    updateAuthControls();
    hideMessage();
    await refreshSignedInViews();
  });

  logoutButton.addEventListener("click", () => {
    currentUser = null;
    updateAuthControls();
    renderNotifications([]);
    dashboardSummary.innerHTML = "";
    popularityChart.innerHTML = "";
    activityMetrics.innerHTML = "";
  });

  updateAuthControls();
  renderNotifications([]);
  fetchActivities();
});

async function loadData() {

    const response = await fetch("./data/latest.json?v=" + Date.now());
    const data = await response.json();

    document.getElementById("update-status").textContent =
        data.status;

    document.getElementById("last-updated").textContent =
        data.lastUpdated;

    renderVideos(data.videos);
}


function renderVideos(videos) {

    const container = document.getElementById("video-cards");

    container.innerHTML = "";

    videos.forEach(video => {

        container.innerHTML += `

        <div class="card">

            <h2>${video.channel}</h2>

            <h3>${video.title}</h3>

            <p>${video.publishDate}</p>

            <p>
                <a href="${video.url}" target="_blank">
                    ${video.url}
                </a>
            </p>

        </div>

        `;
    });
}

loadData();

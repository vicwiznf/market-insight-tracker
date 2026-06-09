async function loadData() {
  try {
    const response = await fetch("./data/latest.json");
    const data = await response.json();

    document.getElementById("update-status").textContent =
      data.status;

    document.getElementById("last-updated").textContent =
      data.lastUpdated;

    const cardsContainer = document.getElementById("video-cards");

    cardsContainer.innerHTML = "";

    data.videos.forEach(video => {
      cardsContainer.innerHTML += `
        <div class="card">
          <h2>${video.channel}</h2>
          <br>
          <p><strong>標題：</strong>${video.title}</p>
          <p><strong>發布時間：</strong>${video.publishDate}</p>
          <p><a href="${video.url}" target="_blank">觀看影片</a></p>
          <br>
          <p>${video.summary}</p>
        </div>
      `;
    });

    document.getElementById("consensus").innerHTML =
      data.consensus;
  } catch (error) {
    console.error(error);
  }
}

loadData();

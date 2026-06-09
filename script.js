async function loadData() {
  try {
    const response = await fetch("./data/latest.json");
    const data = await response.json();

    document.getElementById("update-status").textContent = data.status;
    document.getElementById("last-updated").textContent = data.lastUpdated;

    renderVideos(data.videos);
    renderConsensus(data.consensus);

  } catch (error) {
    console.error(error);
    document.getElementById("update-status").textContent = "資料讀取失敗";
  }
}

function renderVideos(videos) {
  const cardsContainer = document.getElementById("video-cards");
  cardsContainer.innerHTML = "";

  videos.forEach(video => {
    const highlightsHtml = video.highlights
      .map(item => `<li>${item}</li>`)
      .join("");

    cardsContainer.innerHTML += `
      <article class="card">
        <div class="card-header">
          <h2>${video.channel}</h2>
          <a href="${video.url}" target="_blank">觀看影片</a>
        </div>

        <p class="meta">${video.publishDate}</p>
        <h3>${video.title}</h3>

        <section>
          <h4>300 字摘要</h4>
          <p>${video.summary}</p>
        </section>

        <section>
          <h4>五個重點</h4>
          <ul>${highlightsHtml}</ul>
        </section>

        <section>
          <h4>投資啟發</h4>
          <p><strong>短期：</strong>${video.investmentInsight.shortTerm}</p>
          <p><strong>中期：</strong>${video.investmentInsight.midTerm}</p>
          <p><strong>長期：</strong>${video.investmentInsight.longTerm}</p>
        </section>

        <section>
          <h4>注意事項</h4>
          <p>${video.warning}</p>
        </section>
      </article>
    `;
  });
}

function renderConsensus(consensus) {
  document.getElementById("consensus").innerHTML = `
    <div class="consensus-grid">
      <div>
        <h3>共同關注主題</h3>
        <ul>${consensus.commonTopics.map(item => `<li>${item}</li>`).join("")}</ul>
      </div>

      <div>
        <h3>有分歧的議題</h3>
        <ul>${consensus.differentViews.map(item => `<li>${item}</li>`).join("")}</ul>
      </div>

      <div>
        <h3>今日市場焦點</h3>
        <ul>${consensus.marketFocus.map(item => `<li>${item}</li>`).join("")}</ul>
      </div>
    </div>
  `;
}

loadData();

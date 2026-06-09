async function loadData() {

    const response = await fetch("./data/latest.json?v=" + Date.now());
    const data = await response.json();

    document.getElementById("update-status").textContent =
        data.status;

    document.getElementById("last-updated").textContent =
        data.lastUpdated;

    renderVideos(data.videos);
    renderConsensus(data.consensus);
}

function renderVideos(videos) {

    const container = document.getElementById("video-cards");

    container.innerHTML = "";

    videos.forEach(video => {

        const highlights = video.highlights
            .map(item => `<li>${item}</li>`)
            .join("");

        const transcriptPath = video.transcriptPath || "";
        const transcriptLink = transcriptPath
            ? `<a href="${transcriptPath}" target="_blank">查看完整逐字稿</a>`
            : `<span>無逐字稿</span>`;

        const chunkCount = video.chunkCount || 0;

        container.innerHTML += `
        <div class="card">

            <div class="card-header">
                <h2>${video.channel}</h2>
                <a href="${video.url}" target="_blank">
                    觀看影片
                </a>
            </div>

            <div class="meta">
                ${video.publishDate}
            </div>

            <h3>${video.title}</h3>

            <p><strong>逐字稿狀態：</strong>${video.transcriptStatus || "未知"}</p>
            <p><strong>逐字稿來源：</strong>${video.transcriptSource || "未知"}</p>
            <p><strong>逐字稿字數：</strong>${video.transcriptLength || 0}</p>
            <p><strong>分段數量：</strong>${chunkCount}</p>
            <p><strong>逐字稿：</strong>${transcriptLink}</p>

            <section>
                <h4>逐字稿預覽</h4>
                <p>${video.transcriptPreview || "尚無逐字稿預覽。"}</p>
            </section>

            <section>
                <h4>300 字摘要</h4>
                <p>${video.summary}</p>
            </section>

            <section>
                <h4>五個重點</h4>
                <ul>${highlights}</ul>
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

        </div>
        `;
    });

}

function renderConsensus(consensus) {

    document.getElementById("consensus").innerHTML = `

    <div class="consensus-grid">

        <div>
            <h3>共同關注主題</h3>
            <ul>${consensus.commonTopics.map(i => `<li>${i}</li>`).join("")}</ul>
        </div>

        <div>
            <h3>有分歧的議題</h3>
            <ul>${consensus.differentViews.map(i => `<li>${i}</li>`).join("")}</ul>
        </div>

        <div>
            <h3>今日市場焦點</h3>
            <ul>${consensus.marketFocus.map(i => `<li>${i}</li>`).join("")}</ul>
        </div>

    </div>
    `;
}

loadData();

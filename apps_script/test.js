function listAllAdgroups_test_() {
  const campaigns = naverFetch_('GET', '/ncc/campaigns');
  Logger.log('===== 캠페인 ' + campaigns.length + '개 =====');

  campaigns.forEach((c, i) => {
    Logger.log('');
    Logger.log('▶ [' + (i+1) + '] ' + c.name);
    Logger.log('  ID: ' + c.nccCampaignId);
    Logger.log('  customerId: ' + c.customerId);
    Logger.log('  type: ' + c.campaignTp + ' / status: ' + c.status);

    try {
      const adgroups = naverFetch_('GET', '/ncc/adgroups',
        { nccCampaignId: c.nccCampaignId });

      Logger.log('  → 광고그룹 ' + adgroups.length + '개:');
      adgroups.forEach((g, j) => {
        Logger.log('    ' + (j+1) + ') ' + g.name +
                   ' (' + g.nccAdgroupId + ')' +
                   ' / status:' + g.status);
      });

      if (adgroups.length > 0) {
        Logger.log('  [첫 그룹 전체 필드]: ' +
                   JSON.stringify(adgroups[0]).substring(0, 400));
      }
    } catch (e) {
      Logger.log('  광고그룹 조회 실패: ' + e.message);
    }

    Utilities.sleep(300);
  });
}
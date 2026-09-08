import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import main
import report
import store
from scrapers.base import JobItem
from scrapers.generic import GenericScraper


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, value in [
            ('store.DB_PATH', os.path.join(self.tmp.name, 'jobs.db')),
            ('report.REPORT_DIR', self.tmp.name),
            ('config.FILTER_BY_KEYWORDS', False),
            ('config.TARGET_CITIES', ['香港', '深圳']),
            ('config.INCLUDE_UNSPECIFIED_LOCATIONS', True),
            ('config.INCLUDE_APPLICATION_PROGRESS', False),
            ('config.GENERIC_SOURCES', []),
        ]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_chinese_english_and_multi_city_matching(self):
        cases = {
            '香港特別行政區': True, 'Hong Kong SAR': True, 'Hongkong': True,
            'HONG  KONG': True, 'HK': True, 'HK / Singapore': True,
            '深圳市': True, 'Shenzhen, China': True, '上海、深圳': True,
            '上海': False, 'Singapore': False, 'Shenzhenville': False,
            'HKUST': False, '': True, '全国': True, '多地': True,
        }
        for location, expected in cases.items():
            with self.subTest(location=location):
                self.assertEqual(report._match_city(JobItem('A', '1', 'Analyst', location=location)), expected)

    def test_no_role_restriction_and_optional_unknown_exclusion(self):
        jobs = [JobItem('A', '1', 'Investment Banking Analyst', location='Hong Kong')]
        self.assertEqual(report.filter_jobs(jobs), jobs)
        with patch('config.INCLUDE_UNSPECIFIED_LOCATIONS', False):
            self.assertFalse(report._match_city(JobItem('A', '2', 'Analyst')))

    def test_stable_ids_update_without_becoming_new(self):
        job = JobItem('A', '1', 'Analyst', location='香港')
        self.assertEqual(store.save_jobs([job]), {'A::1'})
        job.title = 'Updated Analyst'
        self.assertEqual(store.save_jobs([job]), set())
        self.assertEqual(store.save_jobs([JobItem('B', '1', 'Analyst')]), {'B::1'})
        self.assertEqual(store.get_all_jobs_count(), 2)

    def test_full_refuses_to_erase_history(self):
        store.save_jobs([JobItem('A', '1', 'Analyst')])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            main.main(['--full', '--no-push'])
        self.assertEqual(result.exception.code, 2)
        self.assertEqual(store.get_all_jobs_count(), 1)

    def run_scan(self, jobs, *args):
        scraper = Mock()
        scraper.return_value.fetch.return_value = jobs
        with patch('main.SCRAPERS', {'test': scraper}), patch('main.make_session'), \
                patch('push.send_brief') as send, contextlib.redirect_stdout(io.StringIO()):
            content = main.main(list(args))
        return content, send

    def test_first_run_baseline_then_only_new_target_notification(self):
        first = JobItem('test', '1', 'Analyst', location='HK')
        self.run_scan([first], '--no-push')
        second = JobItem('test', '2', 'Analyst', location='深圳')
        outside = JobItem('test', '3', 'Analyst', location='北京')
        _, send = self.run_scan([first, second, outside])
        self.assertEqual(send.call_count, 1)
        self.assertIn('1个新岗位', send.call_args.kwargs['title'])
        _, send_again = self.run_scan([first, second, outside])
        send_again.assert_not_called()

    def test_aggregated_counts_and_failure_are_visible(self):
        job = JobItem('offerstar·A', '1', 'Analyst', location='HK')
        content = report.generate_brief([job], {job.dedup_key}, {'offerstar': 1, 'broken': 0}, {'broken': '接口异常'})
        self.assertIn('| offerstar | 1 | 1 | 1 |', content)
        self.assertIn('| broken | 失败 |', content)
        self.assertIn('抓取异常', content)
        self.assertIn('不限岗位方向', content)

    def test_strict_scan_keeps_successful_data_when_another_source_fails(self):
        good, bad = Mock(), Mock()
        good.return_value.fetch.return_value = [JobItem('good', '1', 'Analyst', location='HK')]
        bad.return_value.fetch.side_effect = ValueError('接口异常')
        with patch('main.SCRAPERS', {'good': good, 'bad': bad}), patch('main.make_session'), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaises(SystemExit) as result:
            main.main(['--strict', '--no-push'])
        self.assertEqual(result.exception.code, 1)
        self.assertEqual(store.get_all_jobs_count(), 1)
        with open(os.path.join(self.tmp.name, 'latest.json'), encoding='utf-8') as handle:
            summary = json.load(handle)
        self.assertIn('bad', summary['errors'])
        self.assertEqual(summary['matching'], 1)

    def test_generic_invalid_response_is_not_zero_jobs(self):
        session = Mock()
        session.get.return_value.json.return_value = {'error': 'unauthorized'}
        scraper = GenericScraper(session, {'name': 'test', 'url': 'https://example.com/jobs'})
        with self.assertRaises(ValueError):
            scraper.fetch()


if __name__ == '__main__':
    unittest.main()

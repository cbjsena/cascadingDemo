import csv
import io


class CsvManager:
    """
    데이터 리스트를 CSV 포맷으로 변환하는 공통 유틸리티
    """

    def create_csv(self, data_rows, headers_config):
        """
        :param data_rows: 데이터 딕셔너리 리스트 (예: [{'no': 1, 'port_code': 'PUS'...}, ...])
        :param headers_config: Config의 grid_headers 튜플 리스트 [(Label, Key, ColIdx), ...]
        :return: CSV 문자열
        """
        output = io.StringIO()

        # 1. 한글 깨짐 방지를 위한 BOM(Byte Order Mark) 추가
        output.write('\ufeff')

        writer = csv.writer(output)

        # 2. CSV 헤더 작성
        # headers_config의 첫 번째 요소(Label)를 사용
        # CSV 헤더에는 줄바꿈(\n)이 있으면 보기 안 좋으므로 공백으로 치환
        labels = [item[0].replace('\n', ' ') for item in headers_config]
        writer.writerow(labels)

        # 3. 데이터 작성
        # headers_config의 두 번째 요소(Key)를 사용하여 데이터 추출
        keys = [item[1] for item in headers_config]

        for row in data_rows:
            row_values = []
            for key in keys:
                val = row.get(key, '')
                # None 데이터 처리
                if val is None:
                    val = ''
                row_values.append(str(val))
            writer.writerow(row_values)

        return output.getvalue()
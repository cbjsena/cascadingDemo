/**
 * static/js/common_api.js
 * 프로젝트 전반에서 사용하는 공통 API 호출 및 Select Box 제어 모듈
 */

const CommonApi = {
    // --- 1. UI Helpers (Select Box 제어) ---

    // Select Box 초기화 (옵션 비우기 & 비활성화)
    resetSelect: function(element, placeholder) {
        if (!element) return;
        element.innerHTML = `<option value="">${placeholder}</option>`;
        element.disabled = true;
    },

    // Select Box 옵션 채우기
    populateSelect: function(element, options, selectedValue = null) {
        if (!element) return;

		// 첫 번째 옵션(Placeholder)만 남기고 나머지 삭제
        const placeholder = element.options[0] ? element.options[0].outerHTML : '<option value="">Select</option>';
        element.innerHTML = placeholder;

        // 데이터가 없거나 배열이 아닐 때 "No data" 처리
        if (!options || !Array.isArray(options) || options.length === 0) {
            const noDataOption = document.createElement('option');
            noDataOption.value = "";
            noDataOption.textContent = "데이터가 없습니다"; // 필요에 따라 텍스트 수정
            element.appendChild(noDataOption);
            element.disabled = true;
            return;
        }

        options.forEach(opt => {
            const option = document.createElement('option');

            // 장고에서 Dict 형태(객체)로 데이터를 보낼 경우를 대비한 안전망
            const val = typeof opt === 'object' ? (opt.id || opt.code || opt.value) : opt;
            const txt = typeof opt === 'object' ? (opt.name || opt.text || opt.label) : opt;

            option.value = val;
            option.textContent = txt;

            if (selectedValue && val === selectedValue) {
                option.selected = true;
            }
            element.appendChild(option);
        });

        // 옵션이 채워졌으면 활성화
        element.disabled = false;
    },

    // --- 2. Data Fetchers (API 호출) ---

    // 공통 Fetch 에러 핸들링 헬퍼 함수 추가
    _handleFetchResponse: async function(res) {
        if (!res.ok) {
            // 장고에서 보낸 에러 메시지가 있다면 추출, 없으면 HTTP 상태 코드
            const text = await res.text();
            throw new Error(`HTTP Error ${res.status}: ${text.substring(0, 100)}...`);
        }
        return res.json();
    },

	// Lane 목록 로드 (Cascade Step 1)
    loadLanes: function(apiUrl, scenarioId, targetElement, callback = null) {
        if (!scenarioId) return;

        fetch(`${apiUrl}?scenario_id=${scenarioId}`)
            .then(this._handleFetchResponse) // HTTP 에러 체크 추가
            .then(data => {
                if (targetElement) {
                    this.populateSelect(targetElement, data.options);
                }
                if (callback) callback(data);
            })
            .catch(err => {
                console.error("Error loading lanes:", err);
                // 에러 발생 시 UI도 초기화 혹은 에러 상태로 변경
                if(targetElement) this.populateSelect(targetElement, []);
            });
    },

    // Proforma 목록 로드 (Cascade Step 2)
    loadProformas: function(apiUrl, scenarioId, laneCode, targetElement, callback = null) {
        if (!scenarioId || !laneCode) return;

        fetch(`${apiUrl}?scenario_id=${scenarioId}&lane_code=${laneCode}`)
            .then(this._handleFetchResponse)
            .then(data => {
                if (targetElement) {
                    this.populateSelect(targetElement, data.options);
                }
                if (callback) callback(data);
            })
            .catch(err => {
                console.error("Error loading proformas:", err);
                if(targetElement) this.populateSelect(targetElement, []);
            });
    },

    // 선박 옵션 목록 로드 (검색 필터용 - LRS 테이블 기준)
    loadVesselOptions: function(apiUrl, scenarioId, laneCode, targetElement, callback = null) {
        // scenarioId가 없으면 빈 배열 처리 후 종료
        if (!scenarioId) {
            if (targetElement) this.populateSelect(targetElement, []);
            return;
        }

        // URL 파라미터 동적 구성 (laneCode는 값이 있을 때만 추가)
        const params = new URLSearchParams({ scenario_id: scenarioId });
        if (laneCode) {
            params.append('lane_code', laneCode);
        }

        fetch(`${apiUrl}?${params.toString()}`)
            .then(this._handleFetchResponse) // HTTP 에러 핸들링
            .then(data => {
                // targetElement(Select Box)가 전달되었다면 옵션 채우기
                if (targetElement) {
                    this.populateSelect(targetElement, data.options);
                }
                // 추가적인 로직이 필요하다면 콜백 실행
                if (callback) callback(data);
            })
            .catch(err => {
                console.error("Error loading vessel options:", err);
                // 에러 발생 시 UI를 "데이터 없음" 상태로 초기화
                if (targetElement) this.populateSelect(targetElement, []);
                if (callback) callback({ options: [] });
            });
    },

    // 선박 목록 로드 (Create 화면용 - Capacity 정보 포함)
    // Select Box를 직접 채우지 않고 데이터 배열을 반환합니다.
    loadVesselList: function(apiUrl, scenarioId, callback) {
        if (!scenarioId) return;

        fetch(`${apiUrl}?scenario_id=${scenarioId}`)
            .then(this._handleFetchResponse)
            .then(data => {
                if (callback) callback(data.vessels || []);
            })
            .catch(err => {
                console.error("Error loading vessel list:", err);
                // 에러 발생 시 빈 배열을 반환하여 로딩 인디케이터 무한루프 등 UI 멈춤 방지
                if (callback) callback([]);
            });
    },

    // 선박 기간 점유 확인 (Lane Check)
    checkVesselLane: function(apiUrl, params, callback) {
        const query = new URLSearchParams(params).toString();

        fetch(`${apiUrl}?${query}`)
            .then(this._handleFetchResponse)
            .then(data => {
                if (callback) callback(data);
            })
            .catch(err => {
                console.error("Error checking vessel lane:", err);
                // 에러 발생 시 UI에서 예외 처리를 할 수 있도록 에러 상태 객체 반환
                if (callback) callback({ error: true, message: err.message });
            });
    }
};
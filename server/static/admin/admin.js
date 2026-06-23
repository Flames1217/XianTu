// 全局变量
      let authToken = localStorage.getItem('admin_token')
      let currentUser = null
      let currentTab = 'players'
      let currentEditItem = null
      const API_BASE = '/api/v1'

      async function readResponsePayload(response) {
        const contentType = response.headers.get('content-type') || ''
        const text = await response.text()
        if (contentType.includes('application/json')) {
          try {
            return { data: JSON.parse(text), text }
          } catch (error) {
            return { data: null, text }
          }
        }
        return { data: null, text }
      }

      // DOM 元素
      const loginContainer = document.getElementById('loginContainer')
      const mainContainer = document.getElementById('mainContainer')
      const loginForm = document.getElementById('loginForm')
      const loginError = document.getElementById('loginError')
      const userInfo = document.getElementById('userInfo')
      const tableContainer = document.getElementById('tableContainer')

      // 初始化
      document.addEventListener('DOMContentLoaded', function () {
        if (authToken) {
          verifyToken()
        } else {
          showLogin()
        }

        // 事件监听
        loginForm.addEventListener('submit', handleLogin)
        document.getElementById('logoutBtn').addEventListener('click', handleLogout)
        document.getElementById('refreshBtn').addEventListener('click', refreshCurrentTab)
        document
          .getElementById('changePasswordBtn')
          .addEventListener('click', showChangePasswordModal)
        document.getElementById('addItemBtn').addEventListener('click', showAddItemModal)

        // 标签页切换
        document.querySelectorAll('.tab-btn').forEach((btn) => {
          btn.addEventListener('click', function () {
            switchTab(this.dataset.tab)
          })
        })

        // 修改密码表单
        document
          .getElementById('changePasswordForm')
          .addEventListener('submit', handleChangePassword)

        // 编辑表单
        document.getElementById('editForm').addEventListener('submit', handleEditSubmit)

        // 封号表单
        document.getElementById('banForm').addEventListener('submit', handleBanSubmit)

        // 监听封号类型变化
        document.getElementById('banType').addEventListener('change', function () {
          const endTimeGroup = document.getElementById('banEndTimeGroup')
          if (this.value === 'permanent') {
            endTimeGroup.style.display = 'none'
          } else {
            endTimeGroup.style.display = 'block'
          }
        })
      })

      // 显示登录界面
      function showLogin() {
        loginContainer.classList.remove('hidden')
        mainContainer.style.display = 'none'
      }

      // 显示主界面
      function showMain() {
        loginContainer.classList.add('hidden')
        mainContainer.style.display = 'block'
        userInfo.textContent = `欢迎，${currentUser.user_name} 仙官 (${currentUser.role === 'super_admin' ? '超级管理员' : '普通管理员'})`
        loadTabData(currentTab)
      }

      // 验证token
      async function verifyToken() {
        try {
          const response = await fetch(`${API_BASE}/admin/me`, {
            headers: {
              Authorization: `Bearer ${authToken}`,
            },
          })

          if (response.ok) {
            currentUser = await response.json()
            showMain()
          } else {
            throw new Error('Token无效')
          }
        } catch (error) {
          console.error('Token验证失败:', error)
          localStorage.removeItem('admin_token')
          authToken = null
          showLogin()
          showError('自动登录失败或令牌已过期，请重新登录。')
        }
      }

      // 处理登录
      async function handleLogin(e) {
        e.preventDefault()
        hideError()

        const username = document.getElementById('username').value
        const password = document.getElementById('password').value

        try {
          const response = await fetch(`${API_BASE}/admin/token`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
          })

          const data = await response.json()

          if (response.ok) {
            authToken = data.access_token
            localStorage.setItem('admin_token', authToken)

            // 获取用户信息
            const userResponse = await fetch(`${API_BASE}/admin/me`, {
              headers: {
                Authorization: `Bearer ${authToken}`,
              },
            })

            currentUser = await userResponse.json()
            showMain()
            hideError()
          } else {
            showError(data.detail || '登录失败')
          }
        } catch (error) {
          console.error('登录错误:', error)
          showError('网络连接失败，请检查后端服务是否启动')
        }
      }

      // 处理登出
      function handleLogout() {
        localStorage.removeItem('admin_token')
        authToken = null
        currentUser = null
        showLogin()
      }

      // 显示错误信息
      function showError(message) {
        loginError.textContent = message
        loginError.classList.remove('hidden')
      }

      // 隐藏错误信息
      function hideError() {
        loginError.classList.add('hidden')
      }

      // 切换标签页
      function switchTab(tabName) {
        currentTab = tabName

        // 更新标签页样式
        document.querySelectorAll('.tab-btn').forEach((btn) => {
          btn.classList.remove('active')
        })
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active')

        // 显示/隐藏添加按钮
        const addBtn = document.getElementById('addItemBtn')
        const canAdd =
          (tabName === 'admins' && currentUser?.role === 'super_admin') ||
          (tabName === 'codes' &&
            (currentUser?.role === 'super_admin' || currentUser?.role === 'admin')) ||
          (tabName === 'talents' && currentUser?.role === 'super_admin') ||
          (tabName === 'talent_tiers' && currentUser?.role === 'super_admin') ||
          (tabName === 'players' && currentUser?.role === 'super_admin') ||
          (tabName === 'worlds' && currentUser?.role === 'super_admin') ||
          (tabName === 'origins' && currentUser?.role === 'super_admin') ||
          (tabName === 'spirit_roots' && currentUser?.role === 'super_admin') ||
          (tabName === 'characters' && currentUser?.role === 'super_admin') ||
          (tabName === 'ban_records' && currentUser?.role === 'super_admin')

        if (canAdd) {
          addBtn.classList.remove('hidden')
          // 更新按钮文本
          if (tabName === 'ban_records') {
            addBtn.textContent = '🚫 封禁玩家'
          } else if (tabName === 'characters') {
            addBtn.textContent = '👤 创建角色'
          } else {
            addBtn.textContent = '➕ 添加'
          }
        } else {
          addBtn.classList.add('hidden')
        }

        loadTabData(tabName)
      }

      // 刷新当前标签页
      function refreshCurrentTab() {
        loadTabData(currentTab)
      }

      // 加载标签页数据
      async function loadTabData(tabName) {
        showLoading()

        if (!authToken) {
          console.error('无授权令牌，无法加载数据。')
          showTableError('授权已失效，请重新登录。')
          // 延迟一小段时间后强制登出
          setTimeout(handleLogout, 1500)
          return
        }

        try {
          let endpoint, columns, formatRow

          switch (tabName) {
            case 'players':
              endpoint = '/users/'
              columns = ['ID', '用户名', '创建时间', '状态', '操作']
              formatRow = (item) => {
                const canEdit = currentUser?.role === 'super_admin'
                const canBan = currentUser?.role === 'super_admin'
                let actions = ''
                if (canEdit) {
                  actions += `<button class="action-btn edit" onclick="editItem('${tabName}', ${item.id})">编辑</button>`
                }
                if (canBan && !item.is_banned) {
                  actions += `<button class="action-btn delete" onclick="banPlayer(${item.id})">封号</button>`
                }
                if (canBan && item.is_banned) {
                  actions += `<button class="action-btn" style="background: var(--success)" onclick="unbanPlayer(${item.id}, '${item.user_name}')">解封</button>`
                }
                // 只有超级管理员可以删除玩家
                if (currentUser?.role === 'super_admin') {
                  actions += ` <button class="action-btn delete" onclick="deleteItem('${tabName}', ${item.id})">删除</button>`
                }
                return [
                  item.id,
                  item.user_name,
                  new Date(item.created_at).toLocaleString('zh-CN'),
                  `<span class="status-badge ${item.is_banned ? 'status-banned' : 'status-active'}">${item.is_banned ? '已封禁' : '正常'}</span>`,
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'characters':
              endpoint = '/admin/characters'
              columns = ['ID', '角色名', '玩家', '世界', '状态', '最后同步时间', '操作']
              formatRow = (item) => {
                const canView = currentUser?.role === 'super_admin' || currentUser?.role === 'admin'
                let actions = ''
                if (canView) {
                  actions += `<button class="action-btn edit" onclick="viewCharacterDetails(${item.id})">详情</button>`
                  if (item.is_deleted) {
                    // 恢复功能待定
                    // actions += `<button class="action-btn" style="background: var(--success)" onclick="restoreCharacter(${item.id})">恢复</button>`;
                  } else {
                    actions += `<button class="action-btn delete" onclick="deleteCharacter(${item.id})">删除</button>`
                  }
                }
                const baseInfo = item.base_info || {}
                const saveInfo = item.game_save || {}
                return [
                  item.id,
                  baseInfo.名字 || '未知',
                  item.player_name || `用户${item.player_id}`,
                  baseInfo.世界 || '未知',
                  `<span class="status-badge ${item.is_deleted ? 'status-banned' : 'status-active'}">${item.is_deleted ? '已删除' : '正常'}</span>`,
                  saveInfo.last_sync_time
                    ? new Date(saveInfo.last_sync_time).toLocaleString('zh-CN')
                    : '从未同步',
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'ban_records':
              endpoint = '/ban/ban_records'
              columns = ['ID', '玩家', '封号类型', '原因', '开始时间', '结束时间', '状态', '操作']
              formatRow = (item) => {
                const canManage =
                  currentUser?.role === 'super_admin' || currentUser?.role === 'admin'
                let actions = ''
                if (canManage && item.is_active) {
                  actions += `<button class="action-btn" style="background: var(--success)" onclick="liftBan(${item.id})">解封</button>`
                }
                return [
                  item.id,
                  item.player_name || `用户${item.player_id}`,
                  item.ban_type === 'permanent' ? '永久封号' : '临时封号',
                  item.reason.length > 30 ? item.reason.substring(0, 30) + '...' : item.reason,
                  new Date(item.ban_start_time).toLocaleString('zh-CN'),
                  item.ban_end_time ? new Date(item.ban_end_time).toLocaleString('zh-CN') : '永久',
                  `<span class="status-badge ${item.is_active ? 'status-banned' : 'status-active'}">${item.is_active ? '生效中' : '已失效'}</span>`,
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'appeals':
              endpoint = '/ban/ban_records?appeal_status=pending'
              columns = ['ID', '玩家', '封号原因', '申诉理由', '申诉时间', '操作']
              formatRow = (item) => {
                const canHandle =
                  currentUser?.role === 'super_admin' || currentUser?.role === 'admin'
                let actions = ''
                if (canHandle && item.appeal_status === 'pending') {
                  actions += `<button class="action-btn" style="background: var(--success)" onclick="handleAppeal(${item.id}, true)">批准</button>`
                  actions += `<button class="action-btn delete" onclick="handleAppeal(${item.id}, false)">拒绝</button>`
                }
                return [
                  item.id,
                  item.player_name || `用户${item.player_id}`,
                  item.reason.length > 20 ? item.reason.substring(0, 20) + '...' : item.reason,
                  item.appeal_reason
                    ? item.appeal_reason.length > 30
                      ? item.appeal_reason.substring(0, 30) + '...'
                      : item.appeal_reason
                    : '-',
                  item.appeal_time ? new Date(item.appeal_time).toLocaleString('zh-CN') : '-',
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'admins':
              endpoint = '/admin/accounts/'
              columns = ['ID', '仙官道号', '品阶', '授印时间', '操作']
              formatRow = (item) => {
                const canEdit = currentUser?.role === 'super_admin' || currentUser?.id === item.id
                const canDelete = currentUser?.role === 'super_admin' && currentUser?.id !== item.id
                let actions = ''
                if (canEdit) {
                  actions += `<button class="action-btn edit" onclick="editItem('${tabName}', ${item.id})">编辑</button>`
                }
                if (canDelete) {
                  actions += `<button class="action-btn delete" onclick="deleteItem('${tabName}', ${item.id})">删除</button>`
                }
                return [
                  item.id,
                  item.user_name,
                  item.role === 'super_admin' ? '超级仙官' : '普通仙官',
                  new Date(item.created_at).toLocaleString('zh-CN'),
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'worlds':
              endpoint = '/worlds/'
              columns = ['ID', '世界名称', '时代', '创建者', '创建时间', '操作']
              formatRow = (item) => {
                const canEdit = currentUser?.role === 'super_admin'
                const canDelete = currentUser?.role === 'super_admin'
                let actions = ''
                if (canEdit) {
                  actions += `<button class="action-btn edit" onclick="editItem('${tabName}', ${item.id})">编辑</button>`
                }
                if (canDelete) {
                  actions += `<button class="action-btn delete" onclick="deleteItem('${tabName}', ${item.id})">删除</button>`
                }
                return [
                  item.id,
                  item.name,
                  item.era || '-',
                  item.creator ? item.creator.user_name : '-',
                  new Date(item.created_at).toLocaleString('zh-CN'),
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'origins':
              endpoint = '/origins/'
              columns = ['ID', '出身名称', '稀有度', '花费点数', '描述', '操作']
              formatRow = (item) => {
                const canEdit = currentUser?.role === 'super_admin'
                const canDelete = currentUser?.role === 'super_admin'
                let actions = ''
                if (canEdit) {
                  actions += `<button class="action-btn edit" onclick="editItem('${tabName}', ${item.id})">编辑</button>`
                }
                if (canDelete) {
                  actions += `<button class="action-btn delete" onclick="deleteItem('${tabName}', ${item.id})">删除</button>`
                }
                return [
                  item.id,
                  item.name,
                  item.rarity || '-',
                  item.talent_cost || 0,
                  item.description
                    ? item.description.length > 50
                      ? item.description.substring(0, 50) + '...'
                      : item.description
                    : '-',
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'talents':
              endpoint = '/talents/'
              columns = ['ID', '天赋名称', '稀有度', '花费点数', '描述', '操作']
              formatRow = (item) => {
                const canManage = currentUser?.role === 'super_admin'
                let actions = ''
                if (canManage) {
                  actions += `<button class="action-btn edit" onclick="editItem('${tabName}', ${item.id})">编辑</button>`
                  actions += `<button class="action-btn delete" onclick="deleteItem('${tabName}', ${item.id})">删除</button>`
                }
                return [
                  item.id,
                  item.name,
                  item.rarity || '-',
                  item.talent_cost || 0,
                  item.description
                    ? item.description.length > 30
                      ? item.description.substring(0, 30) + '...'
                      : item.description
                    : '-',
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'talent_tiers':
              endpoint = '/talent_tiers/'
              columns = ['ID', '天资名称', '稀有度', '总点数', '颜色', '描述', '操作']
              formatRow = (item) => {
                const canManage = currentUser?.role === 'super_admin'
                let actions = ''
                if (canManage) {
                  actions += `<button class="action-btn edit" onclick="editItem('${tabName}', ${item.id})">编辑</button>`
                  actions += `<button class="action-btn delete" onclick="deleteItem('${tabName}', ${item.id})">删除</button>`
                }
                return [
                  item.id,
                  item.name,
                  item.rarity || '-',
                  item.total_points || 0,
                  `<span style="color:${item.color}; font-weight: bold;">${item.color}</span>`,
                  item.description
                    ? item.description.length > 30
                      ? item.description.substring(0, 30) + '...'
                      : item.description
                    : '-',
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'spirit_roots':
              endpoint = '/spirit_roots/'
              columns = ['ID', '灵根名称', '基础倍率', '花费点数', '描述', '操作']
              formatRow = (item) => {
                const canEdit = currentUser?.role === 'super_admin'
                const canDelete = currentUser?.role === 'super_admin'
                let actions = ''
                if (canEdit) {
                  actions += `<button class="action-btn edit" onclick="editItem('${tabName}', ${item.id})">编辑</button>`
                }
                if (canDelete) {
                  actions += `<button class="action-btn delete" onclick="deleteItem('${tabName}', ${item.id})">删除</button>`
                }
                return [
                  item.id,
                  item.name,
                  item.base_multiplier || '-',
                  item.talent_cost || 0,
                  item.description
                    ? item.description.length > 50
                      ? item.description.substring(0, 50) + '...'
                      : item.description
                    : '-',
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'codes':
              endpoint = '/redemption/admin/codes/'
              columns = ['ID', '兑换码', '类型', '使用次数', '创建时间', '操作']
              formatRow = (item) => {
                const canManage =
                  currentUser?.role === 'super_admin' || currentUser?.role === 'admin'
                let actions = ''
                if (canManage) {
                  actions += `<button class="action-btn edit" onclick="editItem('${tabName}', ${item.id})">编辑</button>`
                  actions += `<button class="action-btn delete" onclick="deleteItem('${tabName}', ${item.id})">删除</button>`
                }
                return [
                  item.id,
                  item.code,
                  item.type,
                  `${item.times_used}/${item.max_uses}`,
                  new Date(item.created_at).toLocaleString('zh-CN'),
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'workshop':
              endpoint = '/admin/workshop/items?include_deleted=true&page=1&page_size=100'
              columns = ['ID', '类型', '标题', '作者', '下载', '公开', '删除', '创建时间', '操作']
              formatRow = (item) => {
                const typeMap = {
                  settings: '设置',
                  prompts: '提示词',
                  saves: '单机存档',
                  start_config: '开局配置',
                }
                const canManage =
                  currentUser?.role === 'super_admin' || currentUser?.role === 'admin'
                let actions = ''
                if (canManage) {
                  actions += `<button class="action-btn" onclick="toggleWorkshopPublic(${item.id}, ${item.is_public ? 'false' : 'true'})">${item.is_public ? '隐藏' : '公开'}</button>`
                  if (item.is_deleted) {
                    actions += ` <button class="action-btn" onclick="toggleWorkshopDeleted(${item.id}, false)">恢复</button>`
                  }
                  actions += ` <button class="action-btn delete" onclick="deleteWorkshopItemAdmin(${item.id})">${item.is_deleted ? '彻底删除' : '删除'}</button>`
                }
                const title =
                  item.title && item.title.length > 40
                    ? item.title.substring(0, 40) + '...'
                    : item.title || '-'
                return [
                  item.id,
                  typeMap[item.type] || item.type,
                  title,
                  item.author_name || `用户${item.author_id}`,
                  item.downloads || 0,
                  `<span class="status-badge ${item.is_public ? 'status-active' : 'status-banned'}">${item.is_public ? '公开' : '隐藏'}</span>`,
                  `<span class="status-badge ${item.is_deleted ? 'status-banned' : 'status-active'}">${item.is_deleted ? '已删除' : '正常'}</span>`,
                  item.created_at ? new Date(item.created_at).toLocaleString('zh-CN') : '-',
                  `<div class="action-buttons">${actions}</div>`,
                ]
              }
              break

            case 'system':
              renderSystemSettings()
              return //  直接返回，不走下面的表格渲染逻辑

            default:
              throw new Error('未知的标签页')
          }

          const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
              Authorization: `Bearer ${authToken}`,
            },
          })

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
          }

          const data = await response.json()
          const rows = tabName === 'workshop' ? data.items || [] : data
          displayTable(columns, rows, formatRow)
        } catch (error) {
          console.error('数据加载失败:', error)
          showTableError(`${tabName} 数据加载失败: ${error.message}`)
        }
      }

      // 显示加载状态
      function showLoading() {
        tableContainer.innerHTML = '<div class="loading">⏳ 数据加载中...</div>'
      }

      // 显示表格
      function displayTable(columns, data, formatRow) {
        if (data.length === 0) {
          tableContainer.innerHTML = `
                   <div class="empty-state">
                       <h3>暂无数据</h3>
                       <p>当前分类下还没有任何数据</p>
                   </div>
               `
          return
        }

        const headerHtml = columns.map((col) => `<th>${col}</th>`).join('')
        const rowsHtml = data
          .map((item) => {
            const cells = formatRow(item)
            return `<tr>${cells.map((cell) => `<td>${cell}</td>`).join('')}</tr>`
          })
          .join('')

        tableContainer.innerHTML = `
               <div class="table-container">
                   <table class="table">
                       <thead>
                           <tr>${headerHtml}</tr>
                       </thead>
                       <tbody>
                           ${rowsHtml}
                       </tbody>
                   </table>
               </div>
           `
      }

      // 显示表格错误
      function showTableError(message) {
        tableContainer.innerHTML = `
               <div class="empty-state">
                   <h3>⚠️ 加载失败</h3>
                   <p>${message}</p>
                   <button class="btn btn-primary" onclick="refreshCurrentTab()">重试</button>
               </div>
           `
      }

      // 修改密码功能
      function showChangePasswordModal() {
        document.getElementById('changePasswordModal').classList.remove('hidden')
        document.getElementById('changePasswordForm').reset()
        // 预填充当前用户名
        document.getElementById('currentUserName').value = currentUser.user_name
        document.getElementById('changePasswordError').classList.add('hidden')
      }

      function hideChangePasswordModal() {
        document.getElementById('changePasswordModal').classList.add('hidden')
      }

      async function handleChangePassword(e) {
        e.preventDefault()
        const newUserName = document.getElementById('currentUserName').value
        const current = document.getElementById('currentPassword').value
        const newPass = document.getElementById('newPassword').value
        const confirm = document.getElementById('confirmPassword').value

        if (newPass && newPass !== confirm) {
          document.getElementById('changePasswordError').textContent = '新密码确认不匹配'
          document.getElementById('changePasswordError').classList.remove('hidden')
          return
        }

        try {
          const updates = {
            current_password: current,
          }

          // 只有当用户名发生变化时才更新
          if (newUserName !== currentUser.user_name) {
            updates.user_name = newUserName
          }

          // 只有当新密码不为空时才更新
          if (newPass) {
            updates.password = newPass
          }

          const response = await fetch(`${API_BASE}/admin/accounts/${currentUser.id}`, {
            method: 'PUT',
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(updates),
          })

          if (response.ok) {
            const updatedUser = await response.json()
            currentUser.user_name = updatedUser.user_name
            userInfo.textContent = `欢迎，${currentUser.user_name} 仙官 (${currentUser.role === 'super_admin' ? '超级管理员' : '普通管理员'})`
            hideChangePasswordModal()
            alert('账户信息修改成功！')
          } else {
            const error = await response.json()
            document.getElementById('changePasswordError').textContent = error.detail || '修改失败'
            document.getElementById('changePasswordError').classList.remove('hidden')
          }
        } catch (error) {
          document.getElementById('changePasswordError').textContent = '网络错误'
          document.getElementById('changePasswordError').classList.remove('hidden')
        }
      }

      // 编辑功能
      async function editItem(tabName, itemId) {
        try {
          let endpoint = ''
          switch (tabName) {
            case 'admins':
              endpoint = `/admin/accounts/${itemId}/`
              break
            case 'codes':
              endpoint = `/redemption/admin/codes/${itemId}/`
              break
            case 'talents':
              endpoint = `/talents/${itemId}/`
              break
            case 'talent_tiers':
              endpoint = `/talent_tiers/${itemId}/`
              break
            case 'players':
              endpoint = `/users/${itemId}/`
              break
            case 'worlds':
              endpoint = `/worlds/${itemId}/`
              break
            case 'origins':
              endpoint = `/origins/${itemId}/`
              break
            case 'spirit_roots':
              endpoint = `/spirit_roots/${itemId}/`
              break
            default:
              return
          }

          const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { Authorization: `Bearer ${authToken}` },
          })

          if (response.ok) {
            const item = await response.json()
            currentEditItem = { tabName, itemId, data: item }
            await renderEditForm(tabName, item)
            document.getElementById('editModal').classList.remove('hidden')
          }
        } catch (error) {
          alert('获取数据失败')
        }
      }

      async function renderEditForm(tabName, item) {
        let fields = ''
        let title = ''

        switch (tabName) {
          case 'admins':
            title = '编辑仙官信息'
            fields = `
                       <div class="form-group">
                           <label class="form-label">仙官道号</label>
                           <input type="text" name="user_name" class="form-input" value="${item.user_name || ''}" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">当前密码（修改密码或道号时必填）</label>
                           <input type="password" name="current_password" class="form-input">
                       </div>
                       <div class="form-group">
                           <label class="form-label">新密码（留空不修改）</label>
                           <input type="password" name="password" class="form-input">
                       </div>
                       ${
                         currentUser?.role === 'super_admin'
                           ? `
                       <div class="form-group">
                           <label class="form-label">品阶</label>
                           <select name="role" class="form-select">
                               <option value="admin" ${item.role === 'admin' ? 'selected' : ''}>普通仙官</option>
                               <option value="super_admin" ${item.role === 'super_admin' ? 'selected' : ''}>超级仙官</option>
                           </select>
                       </div>`
                           : ''
                       }
                   `
            break
          case 'codes':
            title = '编辑兑换码'
            fields = `
                       <div class="form-group">
                           <label class="form-label">兑换码</label>
                           <input type="text" name="code" class="form-input" value="${item.code || ''}" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">类型</label>
                           <select name="type" class="form-select" required>
                               <option value="world" ${item.type === 'world' ? 'selected' : ''}>🌍 世界通行证</option>
                               <option value="talent_tier" ${item.type === 'talent_tier' ? 'selected' : ''}>⭐ 天资卷轴</option>
                               <option value="origin" ${item.type === 'origin' ? 'selected' : ''}>👑 出身令牌</option>
                               <option value="spirit_root" ${item.type === 'spirit_root' ? 'selected' : ''}>🌟 灵根玉简</option>
                               <option value="talent" ${item.type === 'talent' ? 'selected' : ''}>💎 天赋秘籍</option>
                           </select>
                       </div>
                       <div class="form-group">
                           <label class="form-label">最大使用次数</label>
                           <input type="number" name="max_uses" class="form-input" value="${item.max_uses || 1}" required>
                       </div>
                   `
            break
          case 'talents':
            title = '编辑天赋'
            fields = `
                       <div class="form-group">
                           <label class="form-label">天赋名称</label>
                           <input type="text" name="name" class="form-input" value="${item.name || ''}" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">稀有度</label>
                           <input type="number" name="rarity" class="form-input" value="${item.rarity || 2}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">花费点数</label>
                           <input type="number" name="talent_cost" class="form-input" value="${item.talent_cost || 1}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">描述</label>
                           <textarea name="description" class="form-input" rows="3">${item.description || ''}</textarea>
                       </div>
                   `
            break
          case 'talent_tiers':
            title = '编辑天资'
            fields = `
                       <div class="form-group">
                           <label class="form-label">天资名称</label>
                           <input type="text" name="name" class="form-input" value="${item.name || ''}" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">稀有度</label>
                           <input type="number" name="rarity" class="form-input" value="${item.rarity || 2}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">总点数</label>
                           <input type="number" name="total_points" class="form-input" value="${item.total_points || 70}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">颜色</label>
                           <input type="text" name="color" class="form-input" value="${item.color || 'white'}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">描述</label>
                           <textarea name="description" class="form-input" rows="3">${item.description || ''}</textarea>
                       </div>
                   `
            break
          case 'players':
            title = '编辑玩家信息'
            fields = `
                       <div class="form-group">
                           <label class="form-label">用户名</label>
                           <input type="text" name="user_name" class="form-input" value="${item.user_name || ''}" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">新密码（留空不修改）</label>
                           <input type="password" name="password" class="form-input">
                       </div>
                       <div class="form-group">
                           <label class="form-label">状态</label>
                           <select name="is_banned" class="form-select">
                               <option value="false" ${!item.is_banned ? 'selected' : ''}>正常</option>
                               <option value="true" ${item.is_banned ? 'selected' : ''}>已封禁</option>
                           </select>
                       </div>
                   `
            break
          case 'worlds':
            title = '编辑世界信息'
            fields = `
                       <div class="form-group">
                           <label class="form-label">世界名称</label>
                           <input type="text" name="name" class="form-input" value="${item.name || ''}" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">时代背景</label>
                           <input type="text" name="era" class="form-input" value="${item.era || ''}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">世界描述</label>
                           <textarea name="description" class="form-input" rows="4">${item.description || ''}</textarea>
                       </div>
                   `
            break
          case 'origins':
            title = '编辑出身信息'
            fields = `
                       <div class="form-group">
                           <label class="form-label">出身名称</label>
                           <input type="text" name="name" class="form-input" value="${item.name || ''}" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">稀有度</label>
                           <input type="number" name="rarity" class="form-input" value="${item.rarity || 3}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">花费点数</label>
                           <input type="number" name="talent_cost" class="form-input" value="${item.talent_cost || 0}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">描述</label>
                           <textarea name="description" class="form-input" rows="3">${item.description || ''}</textarea>
                       </div>
                   `
            break
          case 'spirit_roots':
            title = '编辑灵根信息'
            fields = `
                       <div class="form-group">
                           <label class="form-label">灵根名称</label>
                           <input type="text" name="name" class="form-input" value="${item.name || ''}" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">基础倍率</label>
                           <input type="number" name="base_multiplier" class="form-input" step="0.1" value="${item.base_multiplier || 1.0}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">花费点数</label>
                           <input type="number" name="talent_cost" class="form-input" value="${item.talent_cost || 0}">
                       </div>
                       <div class="form-group">
                           <label class="form-label">描述</label>
                           <textarea name="description" class="form-input" rows="3">${item.description || ''}</textarea>
                       </div>
                   `
            break
        }

        document.getElementById('editModalTitle').textContent = title
        document.getElementById('editFormFields').innerHTML = fields
      }

      function hideEditModal() {
        document.getElementById('editModal').classList.add('hidden')
        currentEditItem = null

        // Restore button default state whenever the modal is hidden
        const submitBtn = document.getElementById('editModalSubmitBtn')
        if (submitBtn) {
          submitBtn.textContent = '保存'
          submitBtn.className = 'btn btn-primary'
          submitBtn.type = 'submit'
          submitBtn.onclick = null
        }
      }

      async function handleEditSubmit(e) {
        e.preventDefault()
        if (!currentEditItem) return

        const formData = new FormData(e.target)
        let payload = {}

        const tabName = currentEditItem.tabName

        switch (tabName) {
          case 'admins':
            payload = {
              user_name: formData.get('user_name'),
              role: formData.get('role'),
            }
            if (formData.get('password')) {
              payload.password = formData.get('password')
            }
            if (
              currentEditItem.itemId &&
              (formData.get('password') ||
                formData.get('user_name') !== currentEditItem.data.user_name)
            ) {
              payload.current_password = formData.get('current_password')
            }
            break
          case 'codes':
            if (currentEditItem.itemId) {
              // 编辑逻辑
              payload = {
                code: formData.get('code'),
                type: formData.get('type'),
                max_uses: parseInt(formData.get('max_uses')) || 1,
              }
            } else {
              // 创建逻辑
              payload = {
                type: formData.get('type'),
                max_uses: parseInt(formData.get('max_uses')) || 1,
                payload: {}, // 根据新后端，payload为空对象
              }
            }
            break
          case 'talents':
            payload = {
              name: formData.get('name'),
              rarity: parseInt(formData.get('rarity')) || 2,
              talent_cost: parseInt(formData.get('talent_cost')) || 1,
              description: formData.get('description'),
            }
            break
          case 'talent_tiers':
            payload = {
              name: formData.get('name'),
              rarity: parseInt(formData.get('rarity')) || 2,
              total_points: parseInt(formData.get('total_points')) || 70,
              color: formData.get('color'),
              description: formData.get('description'),
            }
            break
          case 'players':
            payload = {
              user_name: formData.get('user_name'),
              is_banned: formData.get('is_banned') === 'true',
            }
            if (formData.get('password')) {
              payload.password = formData.get('password')
            }
            break
          case 'worlds':
            payload = {
              name: formData.get('name'),
              era: formData.get('era'),
              description: formData.get('description'),
            }
            // Add creator_id for world creation
            if (!currentEditItem.itemId) {
              payload.creator_id = parseInt(formData.get('creator_id'))
            }
            break
          case 'origins':
            payload = {
              name: formData.get('name'),
              rarity: parseInt(formData.get('rarity')) || 3,
              talent_cost: parseInt(formData.get('talent_cost')) || 0,
              description: formData.get('description'),
            }
            break
          case 'spirit_roots':
            payload = {
              name: formData.get('name'),
              base_multiplier: parseFloat(formData.get('base_multiplier')) || 1.0,
              talent_cost: parseInt(formData.get('talent_cost')) || 0,
              description: formData.get('description'),
            }
            break
          case 'characters':
            // 创建角色的新逻辑
            payload = {
              player_id: parseInt(formData.get('player_id')),
              base_info: {
                名字: formData.get('character_name'),
                年龄: parseInt(formData.get('current_age')) || 16,
                世界: formData.get('world'), // 从 select 获取
                天资: formData.get('talent_tier'),
                出生: formData.get('origin'),
                灵根: formData.get('spirit_root'),
                先天六司: {
                  根骨: parseInt(formData.get('root_bone')),
                  灵性: parseInt(formData.get('spirituality')),
                  悟性: parseInt(formData.get('comprehension')),
                  福缘: parseInt(formData.get('fortune')),
                  魅力: parseInt(formData.get('charm')),
                  心性: parseInt(formData.get('temperament')),
                },
                声望: parseInt(formData.get('reputation')) || 0,
              },
            }
            break
          default:
            for (let [key, value] of formData.entries()) {
              payload[key] = value
            }
            break
        }

        try {
          let endpoint = ''
          let method = 'PUT'

          if (currentEditItem.itemId) {
            // 编辑
            method = 'PUT'
            switch (tabName) {
              case 'admins':
                endpoint = `/admin/accounts/${currentEditItem.itemId}`
                break
              case 'codes':
                endpoint = `/redemption/admin/codes/${currentEditItem.itemId}`
                break
              case 'talents':
                endpoint = `/talents/${currentEditItem.itemId}`
                break
              case 'talent_tiers':
                endpoint = `/talent_tiers/${currentEditItem.itemId}`
                break
              case 'players':
                endpoint = `/users/${currentEditItem.itemId}`
                break
              case 'worlds':
                endpoint = `/worlds/${currentEditItem.itemId}`
                break
              case 'origins':
                endpoint = `/origins/${currentEditItem.itemId}`
                break
              case 'spirit_roots':
                endpoint = `/spirit_roots/${currentEditItem.itemId}`
                break
            }
          } else {
            // 创建
            method = 'POST'
            switch (tabName) {
              case 'admins':
                endpoint = '/admin/accounts'
                break
              case 'codes':
                endpoint = '/redemption/admin/codes'
                break
              case 'talents':
                endpoint = '/talents'
                break
              case 'talent_tiers':
                endpoint = '/talent_tiers'
                break
              case 'players':
                endpoint = '/register'
                break
              case 'worlds':
                endpoint = '/worlds'
                break
              case 'origins':
                endpoint = '/origins'
                break
              case 'spirit_roots':
                endpoint = '/spirit_roots'
                break
              case 'characters':
                endpoint = '/characters/create_by_admin'
                break
            }
          }

          const response = await fetch(`${API_BASE}${endpoint}`, {
            method: method,
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
          })

          if (response.ok) {
            hideEditModal()
            refreshCurrentTab()
          } else {
            const error = await response.json()
            document.getElementById('editError').textContent = error.detail || '保存失败'
            document.getElementById('editError').classList.remove('hidden')
          }
        } catch (error) {
          document.getElementById('editError').textContent = '网络错误'
          document.getElementById('editError').classList.remove('hidden')
        }
      }

      // 删除功能
      async function deleteItem(tabName, itemId) {
        if (!confirm('确定要删除这个项目吗？')) return

        try {
          let endpoint = ''
          switch (tabName) {
            case 'admins':
              endpoint = `/admin/accounts/${itemId}`
              break
            case 'codes':
              endpoint = `/redemption/admin/codes/${itemId}`
              break
            case 'talents':
              endpoint = `/talents/${itemId}`
              break
            case 'talent_tiers':
              endpoint = `/talent_tiers/${itemId}`
              break
            case 'players':
              endpoint = `/users/${itemId}`
              break
            case 'worlds':
              endpoint = `/worlds/${itemId}`
              break
            case 'origins':
              endpoint = `/origins/${itemId}`
              break
            case 'spirit_roots':
              endpoint = `/spirit_roots/${itemId}`
              break
          }

          const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${authToken}` },
          })

          if (response.ok) {
            refreshCurrentTab()
          } else {
            const error = await response.json()
            alert(error.detail || '删除失败')
          }
        } catch (error) {
          alert('网络错误')
        }
      }

      // 添加功能
      async function showAddItemModal() {
        if (currentTab === 'ban_records') {
          banPlayer()
        } else {
          currentEditItem = { tabName: currentTab, itemId: null, data: {} }
          await renderAddForm(currentTab)
          document.getElementById('editModal').classList.remove('hidden')
        }
      }

      async function renderAddForm(tabName) {
        let fields = ''
        let title = ''

        switch (tabName) {
          case 'admins':
            title = '添加新仙官'
            fields = `
                       <div class="form-group">
                           <label class="form-label">仙官道号</label>
                           <input type="text" name="user_name" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">密码</label>
                           <input type="password" name="password" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">品阶</label>
                           <select name="role" class="form-select">
                               <option value="admin">普通仙官</option>
                               <option value="super_admin">超级仙官</option>
                           </select>
                       </div>
                   `
            break
          case 'codes':
            title = '生成天机符箓 (兑换码)'
            fields = `
                       <div class="form-group">
                           <label class="form-label">符箓类型</label>
                           <select name="type" id="codeTypeSelect" class="form-select">
                               <option value="world">🌍 世界通行证</option>
                               <option value="talent_tier">⭐ 天资卷轴</option>
                               <option value="origin">👑 出身令牌</option>
                               <option value="spirit_root">🌟 灵根玉简</option>
                               <option value="talent">💎 天赋秘籍</option>
                           </select>
                           <small style="color: var(--text-light); display: block; margin-top: 5px;">
                               使用时会根据类型自动提供对应的稀有内容
                           </small>
                       </div>
                       <div class="form-group">
                           <label class="form-label">最大使用次数</label>
                           <input type="number" name="max_uses" class="form-input" value="1" min="1" required>
                           <small style="color: var(--text-light); display: block; margin-top: 5px;">
                               设置此兑换码可被使用的次数
                           </small>
                       </div>
                   `
            break
          case 'talents':
            title = '添加新天赋'
            fields = `
                       <div class="form-group">
                           <label class="form-label">天赋名称</label>
                           <input type="text" name="name" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">稀有度</label>
                           <input type="number" name="rarity" class="form-input" value="2">
                       </div>
                       <div class="form-group">
                           <label class="form-label">花费点数</label>
                           <input type="number" name="talent_cost" class="form-input" value="1">
                       </div>
                       <div class="form-group">
                           <label class="form-label">描述</label>
                           <textarea name="description" class="form-input" rows="3"></textarea>
                       </div>
                   `
            break
          case 'talent_tiers':
            title = '添加新天资'
            fields = `
                       <div class="form-group">
                           <label class="form-label">天资名称</label>
                           <input type="text" name="name" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">稀有度</label>
                           <input type="number" name="rarity" class="form-input" value="2">
                       </div>
                       <div class="form-group">
                           <label class="form-label">总点数</label>
                           <input type="number" name="total_points" class="form-input" value="70">
                       </div>
                       <div class="form-group">
                           <label class="form-label">颜色</label>
                           <input type="text" name="color" class="form-input" value="#FFFFFF">
                       </div>
                       <div class="form-group">
                           <label class="form-label">描述</label>
                           <textarea name="description" class="form-input" rows="3"></textarea>
                       </div>
                   `
            break
          case 'players':
            title = '添加新玩家'
            fields = `
                       <div class="form-group">
                           <label class="form-label">用户名</label>
                           <input type="text" name="user_name" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">密码</label>
                           <input type="password" name="password" class="form-input" required>
                       </div>
                   `
            break
          case 'worlds':
            title = '添加新世界'
            fields = `
                       <div class="form-group">
                           <label class="form-label">世界名称</label>
                           <input type="text" name="name" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">时代背景</label>
                           <input type="text" name="era" class="form-input">
                       </div>
                       <div class="form-group">
                           <label class="form-label">世界描述</label>
                           <textarea name="description" class="form-input" rows="4"></textarea>
                       </div>
                       <input type="hidden" name="creator_id" value="${currentUser.id}">
                   `
            break
          case 'origins':
            title = '添加新出身'
            fields = `
                       <div class="form-group">
                           <label class="form-label">出身名称</label>
                           <input type="text" name="name" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">稀有度</label>
                           <input type="number" name="rarity" class="form-input" value="3">
                       </div>
                       <div class="form-group">
                           <label class="form-label">花费点数</label>
                           <input type="number" name="talent_cost" class="form-input" value="0">
                       </div>
                       <div class="form-group">
                           <label class="form-label">描述</label>
                           <textarea name="description" class="form-input" rows="3"></textarea>
                       </div>
                   `
            break
          case 'spirit_roots':
            title = '添加新灵根'
            fields = `
                       <div class="form-group">
                           <label class="form-label">灵根名称</label>
                           <input type="text" name="name" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">基础倍率</label>
                           <input type="number" name="base_multiplier" class="form-input" step="0.1" value="1.0" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">花费点数</label>
                           <input type="number" name="talent_cost" class="form-input" value="0">
                       </div>
                       <div class="form-group">
                           <label class="form-label">描述</label>
                           <textarea name="description" class="form-input" rows="3"></textarea>
                       </div>
                   `
            break
          case 'characters':
            title = '创建新角色'
            // 异步获取下拉列表数据
            let worlds = [],
              talentTiers = [],
              origins = [],
              spiritRoots = []
            try {
              ;[worlds, talentTiers, origins, spiritRoots] = await Promise.all([
                fetch(`${API_BASE}/worlds/`, {
                  headers: { Authorization: `Bearer ${authToken}` },
                }).then((res) => res.json()),
                fetch(`${API_BASE}/talent_tiers/`, {
                  headers: { Authorization: `Bearer ${authToken}` },
                }).then((res) => res.json()),
                fetch(`${API_BASE}/origins/`, {
                  headers: { Authorization: `Bearer ${authToken}` },
                }).then((res) => res.json()),
                fetch(`${API_BASE}/spirit_roots/`, {
                  headers: { Authorization: `Bearer ${authToken}` },
                }).then((res) => res.json()),
              ])
            } catch (e) {
              console.error('Failed to load creation options', e)
            }

            const createOptions = (items, nameKey = 'name') =>
              items
                .map((item) => `<option value="${item[nameKey]}">${item[nameKey]}</option>`)
                .join('')

            fields = `
                       <div class="form-group">
                           <label class="form-label">角色道号</label>
                           <input type="text" name="character_name" class="form-input" required>
                       </div>
                       <div class="form-group">
                           <label class="form-label">所属玩家ID</label>
                           <input type="number" name="player_id" class="form-input" min="1" required>
                       </div>
                        <div class="form-group">
                           <label class="form-label">世界</label>
                           <select name="world" class="form-select" required>${createOptions(worlds)}</select>
                       </div>
                       <div class="form-group">
                           <label class="form-label">天资</label>
                           <select name="talent_tier" class="form-select" required>${createOptions(talentTiers)}</select>
                       </div>
                       <div class="form-group">
                           <label class="form-label">出身</label>
                           <select name="origin" class="form-select" required>${createOptions(origins)}</select>
                       </div>
                       <div class="form-group">
                           <label class="form-label">灵根</label>
                           <select name="spirit_root" class="form-select" required>${createOptions(spiritRoots)}</select>
                       </div>
                       <div class="form-group">
                           <label class="form-label">当前年龄</label>
                           <input type="number" name="current_age" class="form-input" min="0" max="18" value="16" required>
                       </div>
                       <div class="form-group">
                           <h4>先天六司配置 (0-10)</h4>
                       </div>
                       <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                           <div class="form-group"><label class="form-label">根骨</label><input type="number" name="root_bone" class="form-input" min="0" max="10" value="5" required></div>
                           <div class="form-group"><label class="form-label">灵性</label><input type="number" name="spirituality" class="form-input" min="0" max="10" value="5" required></div>
                           <div class="form-group"><label class="form-label">悟性</label><input type="number" name="comprehension" class="form-input" min="0" max="10" value="5" required></div>
                           <div class="form-group"><label class="form-label">福缘</label><input type="number" name="fortune" class="form-input" min="0" max="10" value="5" required></div>
                           <div class="form-group"><label class="form-label">魅力</label><input type="number" name="charm" class="form-input" min="0" max="10" value="5" required></div>
                           <div class="form-group"><label class="form-label">心性</label><input type="number" name="temperament" class="form-input" min="0" max="10" value="5" required></div>
                       </div>
                       <div class="form-group">
                            <label class="form-label">初始声望</label>
                            <input type="number" name="reputation" class="form-input" min="0" value="0" required>
                       </div>
                   `
            break
        }

        document.getElementById('editModalTitle').textContent = title
        document.getElementById('editFormFields').innerHTML = fields
      }

      // 封号相关功能
      function banPlayer(playerId) {
        // playerName is no longer needed
        const banModal = document.getElementById('banModal')
        const banForm = document.getElementById('banForm')

        banForm.reset()
        document.getElementById('banError').classList.add('hidden')

        // Set default end time
        const tomorrow = new Date()
        tomorrow.setDate(tomorrow.getDate() + 1)
        document.getElementById('banEndTime').value = tomorrow.toISOString().slice(0, 16)

        loadPlayersForBanModal(playerId)
        banModal.classList.remove('hidden')
      }

      async function loadPlayersForBanModal(selectedPlayerId) {
        const playerSelect = document.getElementById('banPlayerSelect')
        playerSelect.innerHTML = '<option>加载玩家列表中...</option>'
        playerSelect.disabled = true

        try {
          const response = await fetch(`${API_BASE}/users/`, {
            headers: { Authorization: `Bearer ${authToken}` },
          })
          if (!response.ok) throw new Error('无法获取玩家列表')

          const players = await response.json()
          const normalPlayers = players.filter((p) => !p.is_banned)

          if (selectedPlayerId) {
            const isSelectedPlayerInList = normalPlayers.some((p) => p.id === selectedPlayerId)
            if (!isSelectedPlayerInList) {
              const selectedPlayer = players.find((p) => p.id === selectedPlayerId)
              if (selectedPlayer) {
                normalPlayers.unshift(selectedPlayer)
              }
            }
          }

          if (normalPlayers.length === 0) {
            playerSelect.innerHTML = '<option>无可选玩家</option>'
            return
          }

          playerSelect.innerHTML = '<option value="">请选择一个玩家</option>'
          normalPlayers.forEach((player) => {
            const option = document.createElement('option')
            option.value = player.id
            option.textContent = `${player.user_name} (ID: ${player.id})`
            playerSelect.appendChild(option)
          })

          if (selectedPlayerId) {
            playerSelect.value = selectedPlayerId
          }

          playerSelect.disabled = false
        } catch (error) {
          playerSelect.innerHTML = `<option>加载失败: ${error.message}</option>`
        }
      }

      function hideBanModal() {
        document.getElementById('banModal').classList.add('hidden')
      }

      async function handleBanSubmit(e) {
        e.preventDefault()
        const playerId = document.getElementById('banPlayerSelect').value
        const banType = document.getElementById('banType').value
        const banReason = document.getElementById('banReason').value
        let banEndTime = null
        const banError = document.getElementById('banError')

        if (!playerId) {
          banError.textContent = '请选择一个玩家'
          banError.classList.remove('hidden')
          return
        }

        if (banType === 'temporary') {
          banEndTime = document.getElementById('banEndTime').value
          if (!banEndTime) {
            banError.textContent = '临时封号必须设置结束时间'
            banError.classList.remove('hidden')
            return
          }
        }

        try {
          const payload = {
            player_id: parseInt(playerId),
            ban_type: banType,
            reason: banReason,
          }

          if (banEndTime) {
            payload.ban_end_time = new Date(banEndTime).toISOString()
          }

          const response = await fetch(`${API_BASE}/ban/ban_player`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
          })

          if (response.ok) {
            hideBanModal()
            refreshCurrentTab()
            alert('玩家封禁成功')
          } else {
            const error = await response.json()
            banError.textContent = error.detail || '封禁失败'
            banError.classList.remove('hidden')
          }
        } catch (error) {
          banError.textContent = '网络错误'
          banError.classList.remove('hidden')
        }
      }

      async function unbanPlayer(playerId, playerName) {
        if (!confirm(`确定要解封玩家 "${playerName}" 吗？`)) return

        try {
          const response = await fetch(`${API_BASE}/ban/unban_player/${playerId}`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${authToken}`,
            },
          })

          if (response.ok) {
            refreshCurrentTab()
            alert('玩家解封成功')
          } else {
            const error = await response.json()
            alert(error.detail || '解封失败')
          }
        } catch (error) {
          alert('网络错误')
        }
      }

      async function liftBan(banRecordId) {
        if (!confirm('确定要解除此封号记录吗？')) return

        try {
          const response = await fetch(`${API_BASE}/ban/unban_player/${banRecordId}`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${authToken}`,
            },
          })

          if (response.ok) {
            refreshCurrentTab()
            alert('封号已解除')
          } else {
            const error = await response.json()
            alert(error.detail || '解封失败')
          }
        } catch (error) {
          alert('网络错误')
        }
      }

      async function handleAppeal(banRecordId, approve) {
        const action = approve ? '批准' : '拒绝'
        if (!confirm(`确定要${action}此申诉吗？`)) return

        try {
          const response = await fetch(
            `${API_BASE}/ban/handle_appeal/${banRecordId}?approve=${approve}`,
            {
              method: 'POST',
              headers: {
                Authorization: `Bearer ${authToken}`,
              },
            },
          )

          if (response.ok) {
            refreshCurrentTab()
            alert(`申诉已${action}`)
          } else {
            const error = await response.json()
            alert(error.detail || `${action}申诉失败`)
          }
        } catch (error) {
          alert('网络错误')
        }
      }

      // 角色管理功能
      async function viewCharacterDetails(characterId) {
        try {
          // 获取角色基础信息
          const baseResponse = await fetch(`${API_BASE}/admin/characters/${characterId}`, {
            headers: { Authorization: `Bearer ${authToken}` },
          })

          if (!baseResponse.ok) throw new Error('获取角色基础信息失败')
          const character = await baseResponse.json()

          // 获取游戏状态
          const stateResponse = await fetch(
            `${API_BASE}/admin/characters/${characterId}/gamestate`,
            {
              headers: { Authorization: `Bearer ${authToken}` },
            },
          )

          let gameState = null
          if (stateResponse.ok) {
            gameState = await stateResponse.json()
          }

          displayCharacterDetails(character, gameState)
          document.getElementById('characterModal').classList.remove('hidden')
        } catch (error) {
          console.error('获取角色详情失败:', error)
          alert(`获取角色详情失败: ${error.message}`)
        }
      }

      function displayCharacterDetails(character, gameState) {
        const baseInfo = character.base_info || {}
        document.getElementById('characterModalTitle').textContent =
          `${baseInfo.名字 || '未知角色'} - 详细信息`

        const sixAttrs = baseInfo.先天六司 || {}
        const saveData = gameState ? gameState.save_data || {} : {}
        const playerState = saveData.player_state || {}

        if (!gameState || !gameState.save_data) {
          console.log(`角色 ${character.id} 的游戏状态为空, 前端推演默认值。`)
          playerState.max_qi_blood = 50 + (sixAttrs.根骨 || 5) * 10
          playerState.qi_blood = playerState.max_qi_blood
          playerState.max_spiritual_power = 100 + (sixAttrs.灵性 || 5) * 10
          playerState.spiritual_power = playerState.max_spiritual_power
          playerState.max_spirit_sense = 10 + (sixAttrs.悟性 || 5) * 2
          playerState.spirit_sense = playerState.max_spirit_sense
          playerState.max_lifespan = 60 + (sixAttrs.根骨 || 5) * 2 + (sixAttrs.福缘 || 5)
          playerState.current_age = baseInfo.年龄 || 16
          playerState.spiritual_stones = 10 * (sixAttrs.福缘 || 5)
        }

        let html = `
               <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                   <div>
                       <h4>基础信息</h4>
                       <p><strong>角色ID:</strong> ${character.id}</p>
                       <p><strong>角色名:</strong> ${baseInfo.名字}</p>
                       <p><strong>世界:</strong> ${baseInfo.世界}</p>
                       <p><strong>天资:</strong> ${baseInfo.天资}</p>
                       <p><strong>出身:</strong> ${baseInfo.出生}</p>
                       <p><strong>灵根:</strong> ${baseInfo.灵根}</p>
                       <p><strong>声望:</strong> ${baseInfo.声望 || 0}</p>
                       <p><strong>创建时间:</strong> ${new Date(character.created_at).toLocaleString('zh-CN')}</p>
                       <p><strong>状态:</strong> ${character.is_deleted ? '(已删除)' : '正常'}</p>
                   </div>
                   <div>
                       <h4>先天六司</h4>
                       <p><strong>根骨:</strong> ${sixAttrs.根骨}</p>
                       <p><strong>灵性:</strong> ${sixAttrs.灵性}</p>
                       <p><strong>悟性:</strong> ${sixAttrs.悟性}</p>
                       <p><strong>福缘:</strong> ${sixAttrs.福缘}</p>
                       <p><strong>魅力:</strong> ${sixAttrs.魅力}</p>
                       <p><strong>心性:</strong> ${sixAttrs.心性}</p>
                   </div>
                   <div>
                       <h4>游戏状态</h4>
                       <p><strong>当前境界:</strong> ${playerState.current_realm_name || '凡人'}</p>
                       <p><strong>修炼进度:</strong> ${(playerState.cultivation_progress || 0).toFixed(1)}%</p>
                       <p><strong>修炼经验:</strong> ${(playerState.cultivation_experience || 0).toLocaleString()}</p>
                       <p><strong>当前位置:</strong> ${playerState.current_location_name || '未知'}</p>
                       <p><strong>灵石:</strong> ${(playerState.spiritual_stones || 0).toLocaleString()}</p>
                       <p><strong>气血:</strong> ${playerState.qi_blood || 'N/A'} / ${playerState.max_qi_blood || 'N/A'}</p>
                       <p><strong>灵气:</strong> ${playerState.spiritual_power || 'N/A'} / ${playerState.max_spiritual_power || 'N/A'}</p>
                       <p><strong>神识:</strong> ${playerState.spirit_sense || 'N/A'} / ${playerState.max_spirit_sense || 'N/A'}</p>
                       <p><strong>寿元:</strong> ${playerState.current_age || 'N/A'} / ${playerState.max_lifespan || 'N/A'}</p>
                       <p><strong>最后同步:</strong> ${gameState && gameState.last_sync_time ? new Date(gameState.last_sync_time).toLocaleString('zh-CN') : '从未同步'}</p>
                       <p><strong>数据版本:</strong> ${gameState ? gameState.version : 0}</p>
                   </div>
               </div>
           `

        document.getElementById('characterDetails').innerHTML = html
      }

      function hideCharacterModal() {
        document.getElementById('characterModal').classList.add('hidden')
      }

      async function deleteCharacter(characterId) {
        if (!confirm('确定要删除此角色吗？此操作为软删除。')) return

        try {
          const response = await fetch(`${API_BASE}/admin/characters/${characterId}`, {
            method: 'DELETE',
            headers: {
              Authorization: `Bearer ${authToken}`,
            },
          })

          if (response.ok) {
            refreshCurrentTab()
            alert('角色删除成功')
          } else {
            const error = await response.json()
            alert(error.detail || '删除失败')
          }
        } catch (error) {
          alert('网络错误')
        }
      }

      async function restoreCharacter(characterId) {
        if (!confirm('确定要恢复此角色吗？')) return
        // 待后端实现恢复接口
        alert('恢复功能待实现')
      }

      // 系统设置
      async function renderSystemSettings() {
        showLoading()
        try {
          // 同时获取版本号和安全配置
          const [versionRes, securityRes] = await Promise.all([
            fetch(`${API_BASE}/version`),
            fetch(`${API_BASE}/admin/security-config`, {
              headers: { Authorization: `Bearer ${authToken}` },
            }),
          ])

          let version = '1.0.0'
          if (versionRes.ok) {
            const data = await versionRes.json()
            version = data.version
          }

          let securityConfig = null
          if (securityRes.ok) {
            securityConfig = await securityRes.json()
          }

          tableContainer.innerHTML = `
            <div class="settings-container">
              <!-- 版本设置 -->
              <div class="settings-section">
                <h3 class="settings-title">📦 版本设置</h3>
                <div class="form-group">
                  <label class="form-label">应用版本号 (APP_VERSION)</label>
                  <input type="text" id="appVersionInput" class="form-input" value="${version}">
                  <small style="color: var(--text-light); display: block; margin-top: 5px;">
                    此版本号将显示在应用主界面。
                  </small>
                </div>
                <div class="form-group" style="margin-top: 15px;">
                  <button id="saveVersionBtn" class="btn btn-primary">保存版本</button>
                </div>
              </div>

              ${
                securityConfig
                  ? `
              <!-- Turnstile 设置 -->
              <div class="settings-section">
                <h3 class="settings-title">🛡️ Turnstile 人机验证</h3>
                <div class="form-group">
                  <label class="form-label">
                    <input type="checkbox" id="turnstileEnabled" ${securityConfig.turnstile_enabled ? 'checked' : ''}>
                    启用 Turnstile 验证
                  </label>
                </div>
                <div class="form-group">
                  <label class="form-label">Site Key（前端公钥）</label>
                  <input type="text" id="turnstileSiteKey" class="form-input"
                    value="${securityConfig.turnstile_site_key || ''}" placeholder="0x开头的公钥，用于前端显示验证组件">
                </div>
                <div class="form-group">
                  <label class="form-label">Secret Key（后端私钥）</label>
                  <input type="password" id="turnstileSecretKey" class="form-input"
                    value="${securityConfig.turnstile_secret_key || ''}" placeholder="输入新密钥以更新（留空不修改）">
                </div>
                <div class="form-group">
                  <label class="form-label">验证 URL</label>
                  <input type="text" id="turnstileVerifyUrl" class="form-input"
                    value="${securityConfig.turnstile_verify_url}">
                </div>
                <div class="form-group" style="margin-top: 15px;">
                  <button id="saveTurnstileBtn" class="btn btn-primary">保存 Turnstile 设置</button>
                </div>
              </div>

              <!-- 邮箱验证设置 -->
              <div class="settings-section">
                <h3 class="settings-title">📧 邮箱验证</h3>
                <div class="form-group">
                  <label class="form-label">
                    <input type="checkbox" id="emailEnabled" ${securityConfig.email_verification_enabled ? 'checked' : ''}>
                    启用邮箱验证
                  </label>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">SMTP 服务器</label>
                    <input type="text" id="smtpHost" class="form-input" value="${securityConfig.smtp_host}">
                  </div>
                  <div class="form-group">
                    <label class="form-label">端口</label>
                    <input type="number" id="smtpPort" class="form-input" value="${securityConfig.smtp_port}">
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">SMTP 用户名</label>
                    <input type="text" id="smtpUser" class="form-input" value="${securityConfig.smtp_user || ''}" placeholder="邮箱地址">
                  </div>
                  <div class="form-group">
                    <label class="form-label">SMTP 密码/授权码</label>
                    <input type="password" id="smtpPassword" class="form-input"
                      value="${securityConfig.smtp_password || ''}" placeholder="输入新密码以更新">
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">发件人邮箱</label>
                    <input type="text" id="smtpFromEmail" class="form-input" value="${securityConfig.smtp_from_email || ''}" placeholder="留空则使用用户名">
                  </div>
                  <div class="form-group">
                    <label class="form-label">发件人名称</label>
                    <input type="text" id="smtpFromName" class="form-input" value="${securityConfig.smtp_from_name}">
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">验证码有效期（分钟）</label>
                  <input type="number" id="emailCodeExpire" class="form-input" value="${securityConfig.email_code_expire_minutes}" style="width: 150px;">
                </div>
                <div class="form-group" style="margin-top: 15px;">
                  <button id="saveEmailBtn" class="btn btn-primary">保存邮箱设置</button>
                </div>
              </div>

              <!-- IP 限流设置 -->
              <div class="settings-section">
                <h3 class="settings-title">⏱️ IP 限流</h3>
                <div class="form-group">
                  <label class="form-label">
                    <input type="checkbox" id="rateLimitEnabled" ${securityConfig.register_rate_limit_enabled ? 'checked' : ''}>
                    启用注册限流
                  </label>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">最大注册次数</label>
                    <input type="number" id="rateLimitMax" class="form-input" value="${securityConfig.register_rate_limit_max}" style="width: 150px;">
                  </div>
                  <div class="form-group">
                    <label class="form-label">时间窗口（秒）</label>
                    <input type="number" id="rateLimitWindow" class="form-input" value="${securityConfig.register_rate_limit_window}" style="width: 150px;">
                    <small style="color: var(--text-light); display: block; margin-top: 5px;">
                      ${Math.floor(securityConfig.register_rate_limit_window / 60)} 分钟内最多 ${securityConfig.register_rate_limit_max} 次注册
                    </small>
                  </div>
                </div>
                <div class="form-group" style="margin-top: 15px;">
                  <button id="saveRateLimitBtn" class="btn btn-primary">保存限流设置</button>
                </div>
              </div>
              `
                  : `<div class="settings-section"><p style="color: var(--text-light);">⚠️ 无法加载安全配置（需要超级管理员权限）</p></div>`
              }

              <div id="settingsSaveStatus" class="hidden" style="margin-top: 15px;"></div>
            </div>
          `

          // 绑定事件
          document.getElementById('saveVersionBtn').addEventListener('click', handleSaveVersion)

          if (securityConfig) {
            document.getElementById('saveTurnstileBtn').addEventListener('click', handleSaveTurnstile)
            document.getElementById('saveEmailBtn').addEventListener('click', handleSaveEmail)
            document.getElementById('saveRateLimitBtn').addEventListener('click', handleSaveRateLimit)
          }
        } catch (error) {
          showTableError(`加载系统设置失败: ${error.message}`)
        }
      }

      async function handleSaveTurnstile() {
        const btn = document.getElementById('saveTurnstileBtn')
        const data = {}

        data.turnstile_enabled = document.getElementById('turnstileEnabled').checked

        const siteKey = document.getElementById('turnstileSiteKey').value
        if (siteKey) {
          data.turnstile_site_key = siteKey
        }

        const secretKey = document.getElementById('turnstileSecretKey').value
        // 只有当输入框值不是脱敏后的值时才更新
        if (secretKey && !secretKey.includes('*')) {
          data.turnstile_secret_key = secretKey
        }

        const verifyUrl = document.getElementById('turnstileVerifyUrl').value
        if (verifyUrl) {
          data.turnstile_verify_url = verifyUrl
        }

        await saveSecurityConfig('turnstile', data, btn)
      }

      async function handleSaveEmail() {
        const btn = document.getElementById('saveEmailBtn')
        const data = {}

        data.email_verification_enabled = document.getElementById('emailEnabled').checked

        const smtpHost = document.getElementById('smtpHost').value
        if (smtpHost) data.smtp_host = smtpHost

        const smtpPort = document.getElementById('smtpPort').value
        if (smtpPort) data.smtp_port = parseInt(smtpPort)

        const smtpUser = document.getElementById('smtpUser').value
        if (smtpUser) data.smtp_user = smtpUser

        const smtpPassword = document.getElementById('smtpPassword').value
        if (smtpPassword && !smtpPassword.includes('*')) {
          data.smtp_password = smtpPassword
        }

        const smtpFromEmail = document.getElementById('smtpFromEmail').value
        if (smtpFromEmail) data.smtp_from_email = smtpFromEmail

        const smtpFromName = document.getElementById('smtpFromName').value
        if (smtpFromName) data.smtp_from_name = smtpFromName

        const emailCodeExpire = document.getElementById('emailCodeExpire').value
        if (emailCodeExpire) data.email_code_expire_minutes = parseInt(emailCodeExpire)

        await saveSecurityConfig('email', data, btn)
      }

      async function handleSaveRateLimit() {
        const btn = document.getElementById('saveRateLimitBtn')
        const data = {}

        data.register_rate_limit_enabled = document.getElementById('rateLimitEnabled').checked

        const max = document.getElementById('rateLimitMax').value
        if (max) data.register_rate_limit_max = parseInt(max)

        const window = document.getElementById('rateLimitWindow').value
        if (window) data.register_rate_limit_window = parseInt(window)

        await saveSecurityConfig('rate-limit', data, btn)
      }

      async function saveSecurityConfig(type, data, btn) {
        const saveStatus = document.getElementById('settingsSaveStatus')
        const originalText = btn.textContent

        btn.disabled = true
        btn.textContent = '保存中...'

        try {
          const response = await fetch(`${API_BASE}/admin/security-config/${type}`, {
            method: 'PUT',
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
          })

          const payload = await readResponsePayload(response)
          if (response.ok) {
            const message = payload.data?.message || payload.text || '????'
            saveStatus.textContent = `? ${message}`
            saveStatus.className = 'status-badge status-active'
            // ???????????
            setTimeout(() => renderSystemSettings(), 1500)
          } else {
            const detail = payload.data?.detail || payload.text || '????'
            saveStatus.textContent = `? ????: ${detail}`
            saveStatus.className = 'error-message'
          }
          saveStatus.classList.remove('hidden')
        } catch (error) {
          saveStatus.textContent = `❌ 网络错误: ${error.message}`
          saveStatus.className = 'error-message'
          saveStatus.classList.remove('hidden')
        } finally {
          btn.disabled = false
          btn.textContent = originalText
          setTimeout(() => saveStatus.classList.add('hidden'), 5000)
        }
      }

      async function handleSaveVersion() {
        const newVersion = document.getElementById('appVersionInput').value
        const saveStatus = document.getElementById('settingsSaveStatus')

        if (!newVersion) {
          alert('版本号不能为空')
          return
        }

        const saveBtn = document.getElementById('saveVersionBtn')
        saveBtn.disabled = true
        saveBtn.textContent = '保存中...'

        try {
          const response = await fetch(`${API_BASE}/admin/version`, {
            method: 'PUT',
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ value: newVersion }),
          })

          const payload = await readResponsePayload(response)
          if (response.ok) {
            saveStatus.textContent = '? ?????'
            saveStatus.className = 'status-badge status-active'
          } else {
            const detail = payload.data?.detail || payload.text || '????'
            saveStatus.textContent = `? ????: ${detail}`
            saveStatus.className = 'error-message'
          }
          saveStatus.classList.remove('hidden')
        } catch (error) {
          saveStatus.textContent = `❌ 网络错误: ${error.message}`
          saveStatus.className = 'error-message'
          saveStatus.classList.remove('hidden')
        } finally {
          saveBtn.disabled = false
          saveBtn.textContent = '保存设置'
          setTimeout(() => saveStatus.classList.add('hidden'), 5000)
        }
      }

      // 创意工坊管理
      async function toggleWorkshopPublic(itemId, isPublic) {
        try {
          const response = await fetch(`${API_BASE}/admin/workshop/items/${itemId}/visibility`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ is_public: isPublic }),
          })
          if (response.ok) {
            refreshCurrentTab()
          } else {
            const error = await response.json()
            alert(error.detail || '更新失败')
          }
        } catch (error) {
          alert('网络错误')
        }
      }

      async function toggleWorkshopDeleted(itemId, isDeleted) {
        try {
          const response = await fetch(`${API_BASE}/admin/workshop/items/${itemId}/visibility`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ is_deleted: isDeleted }),
          })
          if (response.ok) {
            refreshCurrentTab()
          } else {
            const error = await response.json()
            alert(error.detail || '更新失败')
          }
        } catch (error) {
          alert('网络错误')
        }
      }

      async function deleteWorkshopItemAdmin(itemId) {
        if (!confirm('确认要永久删除这个创意吗？此操作不可恢复。')) return
        try {
          const response = await fetch(`${API_BASE}/admin/workshop/items/${itemId}`, {
            method: 'DELETE',
            headers: {
              Authorization: `Bearer ${authToken}`,
              'Content-Type': 'application/json',
            },
          })
          if (response.ok) {
            refreshCurrentTab()
          } else {
            const error = await response.json()
            alert(error.detail || '删除失败')
          }
        } catch (error) {
          alert('网络错误')
        }
      }

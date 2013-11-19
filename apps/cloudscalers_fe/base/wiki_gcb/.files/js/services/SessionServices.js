


angular.module('cloudscalers.SessionServices', ['ng'])

	.factory('authenticationInterceptor',['$q','$log', 'APIKey', function($q, $log, APIKey){
        return {
            'request': function(config) {
                if (config) {
                    url = config.url;

                    if(/\/machines\//i.test(url) || /\/sizes\//i.test(url) || /\/images\//i.test(url)) {
                        uri = new URI(url);
                        uri.addSearch('api_key', APIKey.get());
                        config.url = uri.toString();
    				}
                }
                return config || $q.when(config);
    	    },
    	    'response': function(response) {
                $log.log("Response intercepted");
                return response || $q.when(response);
            }
        };
	}])
    .factory('APIKey', function($window) {
        var clientApiKey;
        return {
            get: function() { 
                return $window.localStorage.getItem('gcb:api_key');
            },
            set: function(apiKey) {
                $window.localStorage.setItem('gcb:api_key', apiKey);
            },
            clear: function() {
                $window.localStorage.removeItem('gcb:api_key');
            }
        };
    })
    .factory('User', function ($http, APIKey) {
        var user = {};
        user.login = function (username, password) {
            var loginResult = {api_key: undefined, error: false};
            $http({
                method: 'POST',
                data: {
                    username: username,
                    password: password
                },
                url: cloudspaceconfig.apibaseurl + '/users/authenticate'
            }).
            success(function (data, status, headers, config) {
                loginResult.api_key = data;
                APIKey.set(data);
                loginResult.error = false;
            }).
            error(function (data, status, headers, config) {
                loginResult.api_key = undefined;
                loginResult.error = status;
            });
            return loginResult;
        };

        user.logout = function() {
            APIKey.clear();
        };

        user.signUp = function(username, password) {
            var signUpResult = {};
            $http({
                method: 'POST',
                data: {
                    username: username,
                    password: password
                },
                url: cloudspaceconfig.apibaseurl + '/users/signup'
            })
            .success(function(data, status, headers, config) {
                signUpResult.success = true;
            })
            .error(function(data, status, headers, config) {
                signUpResult.error = data;
            });
            return signUpResult;
        }
        
        return user;
    });
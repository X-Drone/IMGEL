#include <iostream>
#include <async_await>

std::future<Data> fetchData(string url) { return std::async([=](){
Data data = download(url).get();
    Data processed = process(data);
    return processed;

}); }


std::future<bool> pushData(Data data, string url) { return std::async([=](){
bool check = push(url, data).get();
    return check;

}); }


int main()
{
    Data processed_data = (std::async([](string url)[=](){
return fetchData(url);
    
}("google.com")).get();
    if (pushData(processed_data, "my_serv.com").get())
        std::cout << "pushed";
    else std::cout << "not pushed";
}

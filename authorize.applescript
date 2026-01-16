try
    do shell script "xattr -rd com.apple.quarantine /Applications/EPUB-Generator.app" with administrator privileges
    display dialog "✅ 승인이 완료되었습니다! 이제부터 바로 실행하실 수 있습니다." buttons {"확인"} default button "확인"
    do shell script "open /Applications/EPUB-Generator.app"
on error
    display dialog "❌ 승인이 취소되었거나 오류가 발생했습니다. '열기' 버튼을 눌러 승인 과정을 완료해 주세요." buttons {"확인"} default button "확인"
end try
